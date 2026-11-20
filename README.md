# Lunix

Tienda de periféricos y hardware para PC, con inventario y ventas guardados en archivos CSV.

## Tecnologías
- FastAPI
- Pandas
- HTML, CSS, JavaScript
- Chart.js

## Instalación
```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución
```bash
uvicorn main:app --reload
```
Abre `index.html` en el navegador (con Live Server, por ejemplo).

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/productos` | Lista los productos de `productos.csv` |
| POST | `/productos` | Agrega un producto |
| DELETE | `/productos/{id}` | Elimina un producto |
| POST | `/productos/{id}` | Compra un producto y registra la venta |
| GET | `/analitica/kpis` | KPIs: producto estrella, ingresos, transacciones, ticket promedio |
| GET | `/analitica/ingresos-por-producto` | Ingresos agrupados por producto |
| GET | `/analitica/ventas-por-fecha` | Ingresos agrupados por día |

## Archivos de datos
- `productos.csv`: catálogo, con id, nombre, precio y cantidad.
- `ventas.csv`: historial de compras, con fecha, producto, precio, cantidad y total.