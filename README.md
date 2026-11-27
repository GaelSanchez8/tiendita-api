# Lunix

Tienda de periféricos y hardware para PC con inventario, compras, dashboard y análisis de ventas. El inventario y las ventas se guardan en archivos CSV, el histórico masivo en Parquet, y un corte de caja automático mantiene el sistema funcionando 24/7.

## Resumen por unidad

### Unidad 1: API y cliente web
El servidor está construido con FastAPI y expone endpoints REST para consultar, crear y eliminar productos, además de registrar compras. El cliente en HTML, CSS y JavaScript consume la API con `fetch()` sin recargar la página.

### Unidad 2: Validación y concurrencia
Pydantic valida los datos de entrada, por ejemplo que el precio no sea negativo y que la cantidad de compra sea mayor que cero. La API responde 404 cuando un producto no existe y 400 cuando no hay stock suficiente. Un `asyncio.Lock()` protege todas las operaciones que escriben en los archivos, para que dos clientes no descuenten el mismo stock al mismo tiempo.

### Unidad 3: Persistencia y visualización
El inventario se guarda en `productos.csv` y cada compra se registra en `ventas.csv`. Pandas calcula los KPIs y las series para las gráficas, y Chart.js dibuja las gráficas de ingresos por producto y ventas por fecha en el dashboard.

### Unidad 4: Big Data y operación 24/7
`generar_parquet.py` crea 1.5 millones de ventas simuladas con NumPy y Polars, usando los productos reales del catálogo, y las guarda en `ventas.parquet` con el mismo esquema que `ventas.csv`. Los endpoints `/api/analisis/...` leen el histórico con Polars (`scan_parquet` y `scan_csv`) y lo unen con las ventas recientes usando `pl.concat()`, sin modificar el Parquet durante las compras. APScheduler ejecuta cada cierto tiempo el corte de caja, que pasa las ventas del CSV al Parquet y vacía `ventas.csv`, todo dentro del mismo lock.

## Tecnologías y librerías
- FastAPI y Uvicorn
- Pydantic
- Pandas
- Polars
- NumPy
- APScheduler
- HTML, CSS, JavaScript y Chart.js

## Instalación
```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución
1. Generar el histórico (solo si `ventas.parquet` no está en el repositorio):
   ```bash
   python generar_parquet.py
   ```
2. Iniciar el servidor:
   ```bash
   uvicorn main:app --reload
   ```
3. Abrir `index.html` en el navegador, con Live Server por ejemplo.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/productos` | Lista los productos de `productos.csv` |
| POST | `/productos` | Agrega un producto |
| DELETE | `/productos/{id}` | Elimina un producto |
| POST | `/productos/{id}` | Compra un producto, descuenta stock y registra la venta |
| GET | `/analitica/kpis` | KPIs con Pandas sobre `ventas.csv` |
| GET | `/analitica/ingresos-por-producto` | Ingresos por producto con Pandas |
| GET | `/analitica/ventas-por-fecha` | Ingresos por día con Pandas |
| GET | `/api/analisis/kpis` | KPIs con Polars sobre el histórico y las ventas recientes |
| GET | `/api/analisis/mas-vendidos` | Unidades e ingresos por producto con Polars |
| GET | `/api/analisis/ventas-por-fecha` | Ingresos por día con Polars |

El dashboard usa los endpoints `/api/analisis/...`, que incluyen el histórico completo.

## Archivos de datos
- `productos.csv`: catálogo, con `id`, `nombre`, `precio` y `cantidad`.
- `ventas.csv`: compras del turno actual, con `id_venta`, `fecha`, `producto`, `precio`, `cantidad` y `monto_total`. El corte de caja lo vacía.
- `ventas.parquet`: histórico de ventas, con el mismo esquema que `ventas.csv`.