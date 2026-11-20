
const API_URL = "http://127.0.0.1:8000/productos";

const ANALITICA_URL = "http://127.0.0.1:8000/analitica";

const kpiProductoEstrella = document.getElementById("kpiProductoEstrella");
const kpiIngresos = document.getElementById("kpiIngresos");
const kpiTransacciones = document.getElementById("kpiTransacciones");
const kpiTicket = document.getElementById("kpiTicket");
const selectProducto = document.getElementById("selectProducto");
const cantidadCompra = document.getElementById("cantidadCompra");
const btnComprar = document.getElementById("btnComprar");
const formProducto = document.getElementById("formProducto");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");
const mensaje = document.getElementById("mensaje");

let graficoProductos = null;
let graficaFechas = null;

// Mostrar mensajes en la interfaz
function mostrarMensaje(texto, tipo) {
    mensaje.textContent = texto;
    mensaje.className = `alert alert-${tipo}`;
}


// GET: consultar los productos de la API
async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);

        if (!respuesta.ok) {
            throw new Error("No se pudieron obtener los productos");
        }

        const productos = await respuesta.json();

        llenarSelect(productos);

        tablaProductos.innerHTML = "";
        totalProductos.textContent =
            `${productos.length} producto${productos.length !== 1 ? "s" : ""}`;

        if (productos.length === 0) {
            tablaProductos.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">
                        No hay productos registrados.
                    </td>
                </tr>
            `;
            return;
        }

        productos.forEach(producto => {
            const fila = document.createElement("tr");

            fila.innerHTML = `
                <td>${producto.id}</td>
                <td>${producto.nombre}</td>
                <td>$${Number(producto.precio).toFixed(2)}</td>
                <td>${producto.cantidad}</td>
                <td>
                    <button
                        class="btn btn-danger btn-sm"
                        onclick="eliminarProducto(${producto.id})"
                    >
                        Eliminar
                    </button>
                </td>
            `;

            tablaProductos.appendChild(fila);
        });

    } catch (error) {
        mostrarMensaje(
            "No se pudo conectar con la API. Verifica que Uvicorn esté ejecutándose.",
            "danger"
        );

        console.error(error);
    }
}


// POST: enviar un nuevo producto a la API
async function guardarProducto(evento) {
    evento.preventDefault();

    const producto = {
        nombre: document.getElementById("nombre").value.trim(),
        precio: Number(document.getElementById("precio").value),
        cantidad: Number(document.getElementById("cantidad").value)
    };

    try {
        const respuesta = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(producto)
        });

        const resultado = await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(resultado.detail || "No se pudo agregar el producto");
        }

        formProducto.reset();

        mostrarMensaje(
            "Producto agregado correctamente.",
            "success"
        );

        await cargarProductos();

    } catch (error) {
        mostrarMensaje(error.message, "danger");
        console.error(error);
    }
}


// DELETE: eliminar un producto de la API
async function eliminarProducto(id) {
    const confirmar = confirm(
        "¿Seguro que deseas eliminar este producto?"
    );

    if (!confirmar) {
        return;
    }

    try {
        const respuesta = await fetch(`${API_URL}/${id}`, {
            method: "DELETE"
        });

        const resultado = await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(resultado.detail || "No se pudo eliminar el producto");
        }

        mostrarMensaje(
            "Producto eliminado correctamente.",
            "success"
        );

        await cargarProductos();

    } catch (error) {
        mostrarMensaje(error.message, "danger");
        console.error(error);
    }
}


// LLena el <select> de comprar con los productos del CSV
function llenarSelect(productos) {
    selectProducto.innerHTML = "";
    productos.forEach(producto => {
        const option = document.createElement("option");
        option.value = producto.id;
        option.textContent = `${producto.nombre} - $${Number(producto.precio).toFixed(2)}) ${producto.cantidad} en stock`;
        selectProducto.appendChild(option);
    });
}

// KPIs: tarjetas con los datos simples de la API
async function cargarKpis() {
    const respuesta = await fetch(`${ANALITICA_URL}/kpis`);
    const kpis = await respuesta.json();

    kpiProductoEstrella.textContent = kpis.producto_estrella ?? "-";
    kpiIngresos.textContent = `$${Number(kpis.ingresos_totales).toFixed(2)}`;
    kpiTransacciones.textContent = kpis.transacciones;
    kpiTicket.textContent = `$${Number(kpis.ticket_promedio).toFixed(2)}`;
}

// Gráfica de barras: ingresos por producto
function dibujarGraficaProductos(datos) {
    if (graficoProductos) {
        graficoProductos.destroy();
    }

    graficoProductos = new Chart(document.getElementById("graficoProductos"), {
        type: "bar",
        data: {
            labels: datos.map(d => d.producto),
            datasets: [{
                label: "Ingresos ($)",
                data: datos.map(d => d.total),
                backgroundColor: "#0d6efd"
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } }
        }
    });
}

// Gráfica de línea: ingresos por día
function dibujarGraficaFechas(datos) {
    if (graficaFechas) {
        graficaFechas.destroy();
    }

    graficaFechas = new Chart(document.getElementById("graficaFechas"), {
        type: "line",
        data: {
            labels: datos.map(d => d.dia),
            datasets: [{
                label: "Ingresos ($)",
                data: datos.map(d => d.total),
                borderColor: "#0d6efd",
                tension: 0.3
            }]
        },
        options: { responsive: true }
    });
}

// Pide las dos series a la API y dibuja ambas gráficas
async function cargarGraficas() {
    const [respuestaProductos, respuestaFechas] = await Promise.all([
        fetch(`${ANALITICA_URL}/ingresos-por-producto`),
        fetch(`${ANALITICA_URL}/ventas-por-fecha`)
    ]);

    dibujarGraficaProductos(await respuestaProductos.json());
    dibujarGraficaFechas(await respuestaFechas.json());
}

// Actualiza todo el dashboard de una vez
async function actualizarDashboard() {
    try {
        await Promise.all([cargarKpis(), cargarGraficas()]);
    } catch (error) {
        mostrarMensaje("No se pudieron cargar las estadísticas.", "danger");
        console.error(error);
    }
}

// POST: comprar un producto seleccionado
async function comprarProducto() {
    const id = selectProducto.value;
    const cantidad = Number(cantidadCompra.value);

    if (!id) {
        mostrarMensaje("Selecciona un producto.", "warning");
        return;
    }

    try {
        const respuesta = await fetch(`${API_URL}/${id}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ cantidad })
        });

        const resultado = await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(resultado.detail || "No se pudo completar la compra");
        }

        const venta = resultado.venta;
        mostrarMensaje(
            `Compra realizada: ${venta.cantidad} x ${venta.producto} por $${venta.total.toFixed(2)}`,
            "success"
        );

        await cargarProductos();
        await actualizarDashboard();

    } catch (error) {
        mostrarMensaje(error.message, "danger");
        console.error(error);
    }
}



formProducto.addEventListener("submit", guardarProducto);
btnComprar.addEventListener("click", comprarProducto);

// Al abrir la página: primero la tabla y el select, luego el dashboard
document.addEventListener("DOMContentLoaded", async () => {
    await cargarProductos();
    await actualizarDashboard();
});