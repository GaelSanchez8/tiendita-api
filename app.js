
const API_URL = "http://127.0.0.1:8000/productos";

const formProducto = document.getElementById("formProducto");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");
const mensaje = document.getElementById("mensaje");


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


// Evento del formulario
formProducto.addEventListener("submit", guardarProducto);


// Cargar productos al abrir la página
document.addEventListener("DOMContentLoaded", cargarProductos);