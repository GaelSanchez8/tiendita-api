import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from datetime import datetime

app = FastAPI(title="API de Tienda")

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

class COMPRA(BaseModel):
    cantidad: int = Field(gt=0) #gt es para decir que la cantidad debe ser mayor a 0

inventario = [
    {"id": 1, "nombre": "Coca-Cola", "precio": 20.0, "cantidad": 25},
    {"id": 2, "nombre": "Papas", "precio": 15.0, "cantidad": 40},
    {"id": 3, "nombre": "Café", "precio": 18.0, "cantidad": 15},
]


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
async def agregar_producto(producto: Producto):
    df = pd.read_csv(RUTA_PRODUCTOS)
    nuevo_id = 1 if df.empty else int(df["id"].max()) + 1
    nuevo_producto = {
        "id": nuevo_id,
        "nombre": producto.nombre.strip(),
        "precio": producto.precio,
        "cantidad": producto.cantidad,
    }   

    df = pd.concat([df, pd.DataFrame([nuevo_producto])], ignore_index=True)
    df.to_csv(RUTA_PRODUCTOS, index=False)  # Guarda el DataFrame actualizado en el archivo CSV

    return nuevo_producto


    if not nuevo_producto["nombre"]:
        raise HTTPException(
            status_code=400,
            detail="El nombre del producto no puede estar vacío",
        )

    inventario.append(nuevo_producto)
    return nuevo_producto


# DELETE: eliminar un producto por su ID
@app.delete("/productos/{producto_id}")
async def eliminar_producto(producto_id: int): 
    df = pd.read_csv(RUTA_PRODUCTOS)
    #Da un error 404 si no existel producto con el ID especificado
    if producto_id not in df["id"].values: 
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )
    producto_eliminado = df[df["id"] == producto_id].to_dict(orient="records")[0]
    df = df[df["id"] != producto_id]
    df.to_csv(RUTA_PRODUCTOS, index=False)  # Guarda el DataFrame actualizado en el archivo CSV

    return {
        "mensaje": "Producto eliminado correctamente",
        "producto_eliminado": producto_eliminado,
    }

@app.post("/productos/{producto_id}")
async def comprar_producto(producto_id: int, compra: COMPRA):
    df = pd.read_csv(RUTA_PRODUCTOS)
    if producto_id not in df["id"].values:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado",
        )

    indice = df.index[df["id"] == producto_id][0]
    producto = df.loc[indice]

    #Error 400 si la cantidad solicitada excede el stock disponible
    if compra.cantidad > producto["cantidad"]:  
        raise HTTPException(
            status_code=400,
            detail="Cantidad solicitada excede el stock disponible",
        )

    #Se decuenta el stock
    venta = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "producto": str(producto["nombre"]),
        "precio": float(producto["precio"]),
        "cantidad": int(compra.cantidad),
        "total": round(float(producto["precio"]) * int(compra.cantidad), 2),
    }

    ventas = pd.read_csv(RUTA_VENTAS)
    ventas = pd.concat([ventas, pd.DataFrame([venta])], ignore_index=True)
    ventas.to_csv(RUTA_VENTAS, index=False)  # Guarda la venta en'el archivo CSV

    return {
        "mensaje": "Compra realizada correctamente",
        "venta": venta,}

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
    ingresos = round(float(ventas["total"].sum()), 2)
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

    agrupado = ventas.groupby("producto", as_index=False)["total"].sum()
    return agrupado.to_dict(orient="records")


@app.get("/analitica/ventas-por-fecha")
async def ventas_por_fecha():
    ventas = pd.read_csv(RUTA_VENTAS)

    if ventas.empty:
        return []

    ventas["dia"] = ventas["fecha"].str[:10]
    agrupado = ventas.groupby("dia", as_index=False)["total"].sum()
    return agrupado.to_dict(orient="records")