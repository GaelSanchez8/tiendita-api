from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from datetime import datetime
import asyncio

app = FastAPI(title="API de Tienda")
lock = asyncio.Lock()  # Lock para manejar la concurrencia en operaciones de escritura

BASE_DIR = Path(__file__).resolve().parent
RUTA_PRODUCTOS = BASE_DIR / "productos.csv"
RUTA_VENTAS = BASE_DIR / "ventas.csv"

# Permite que el cliente (por ejemplo, Live Server en otro puerto)
# pueda comunicarse con esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Producto(BaseModel):
    nombre: str = Field(min_length=1)
    precio: float = Field(ge=0)
    cantidad: int = Field(ge=0)

class Compra(BaseModel):
    cantidad: int = Field(gt=0)


@app.get("/")
def inicio():
    return {"mensaje": "API de tienda funcionando correctamente"}


# GET: consultar todos los productos
@app.get("/productos")
async def obtener_productos():
    df = pd.read_csv(RUTA_PRODUCTOS)
    return df.to_dict(orient="records")         # Lo convierto a una lista de diccionarios para que FastAPI lo pueda serializar a JSON


# POST: agregar un nuevo producto
@app.post("/productos", status_code=201)
async def agregar_prodcto(producto: Producto):
    async with lock:
        df = pd.read_csv(RUTA_PRODUCTOS)

        nombre = producto.nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400,  detail="El nombre del producto no puede estar vacio")

        nuevo_id = 1 if df.empty else int(df["id"].max()) + 1
        nuevo_producto = {
            "id": nuevo_id,
            "nombre": nombre,
            "precio": producto.precio,
            "cantidad": producto.cantidad,
        }

        df = pd.concat([df, pd.DataFrame([nuevo_producto])], ignore_index = True)
        df.to_csv(RUTA_PRODUCTOS, index=False)
    return nuevo_producto


# DELETE: eliminar un producto por su ID
@app.delete("/productos/{producto_id}")
async def eliminar_producto(producto_id: int):
    async with lock:
        df = pd.read_csv(RUTA_PRODUCTOS)

        if producto_id not in df["id"].values:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        producto_eliminado = df[df["id"] == producto_id].to_dict(orient="records")[0]
        df = df[df["id"] != producto_id]
        df.to_csv(RUTA_PRODUCTOS, index=False)

    return {"mensaje": "Producto eliminado correctamente", "producto": producto_eliminado}

@app.post("/productos/{producto_id}")
async def comprar_producto(producto_id: int, compra: Compra):
    async with lock:
        df = pd.read_csv(RUTA_PRODUCTOS)

        if producto_id not in df["id"].values:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        indice = df.index[df["id"] == producto_id][0]
        producto = df.loc[indice]

        #Error 400 si la cantidad solicitada excede el stock disponible
        if compra.cantidad > producto["cantidad"]:  
            raise HTTPException(status_code=400, detail="Cantidad solicitada excede el stock disponible",)

        #Se decuenta el stock
        df.loc[indice, "cantidad"] = int(producto["cantidad"]) - compra.cantidad
        df.to_csv(RUTA_PRODUCTOS, index=False)

        #Se registra la venta con su propio ID
        ventas = pd.read_csv(RUTA_VENTAS)
        id_venta = 1 if ventas.empty else int(ventas["id_venta"].max()) + 1

        venta = {
            "id_venta": id_venta,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "producto": str(producto["nombre"]),
            "precio": float(producto["precio"]),
            "cantidad": compra.cantidad,
            "monto_total": round(float(producto["precio"]) * compra.cantidad, 2)        
        }

        nueva_venta = pd.DataFrame([venta])
        ventas = nueva_venta if ventas.empty else pd.concat([ventas, nueva_venta], ignore_index=True)
        ventas.to_csv(RUTA_VENTAS, index=False)

    return {"mensaje": "Compra realizada correctamente", "venta": venta,}

#Tarjeta de analítica para obtener KPIs, ingresos por producto y ventas por fecha
@app.get("/analitica/kpis")
async def obtener_kpis():
    ventas = pd.read_csv(RUTA_VENTAS)

    if ventas.empty:
        return {
            "producto_estrella": None,
            "ingresos_totales": 0,
            "transacciones": 0,
            "ticket_promedio": 0,
        }

    unidades_por_producto = ventas.groupby("producto")["cantidad"].sum()
    ingresos = round(float(ventas["monto_total"].sum()), 2)
    transacciones = len(ventas)

    return {
        "producto_estrella": str(unidades_por_producto.idxmax()),
        "ingresos_totales": ingresos,
        "transacciones": transacciones,
        "ticket_promedio": round(ingresos / transacciones, 2),
    }


@app.get("/analitica/ingresos-por-producto")
async def ingresos_por_producto():
    ventas = pd.read_csv(RUTA_VENTAS)

    if ventas.empty:
        return []

    agrupado = ventas.groupby("producto", as_index=False)["monto_total"].sum()
    return agrupado.to_dict(orient="records")


@app.get("/analitica/ventas-por-fecha")
async def ventas_por_fecha():
    ventas = pd.read_csv(RUTA_VENTAS)

    if ventas.empty:
        return []

    ventas["dia"] = ventas["fecha"].str[:10]
    agrupado = ventas.groupby("dia", as_index=False)["monto_total"].sum()
    return agrupado.to_dict(orient="records")