import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd

app = FastAPI(title="API de Tienda")

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
    df = pd.read_csv("productos.csv")
    return df.to_dict(orient="records")         # Lo convierto a una lista de diccionarios para que FastAPI lo pueda serializar a JSON


# POST: agregar un nuevo producto
@app.post("/productos", status_code=201)
async def agregar_producto(producto: Producto):
    df = pd.read_csv("productos.csv")
    nuevo_id = 1 if df.empty else int(df["id"].max()) + 1
    nuevo_producto = {
        "id": nuevo_id,
        "nombre": producto.nombre.strip(),
        "precio": producto.precio,
        "cantidad": producto.cantidad,
    }   

    df = pd.concat([df, pd.DataFrame([nuevo_producto])], ignore_index=True)
    df.to_csv("productos.csv", index=False)  # Guarda el DataFrame actualizado en el archivo CSV

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
    await asyncio.sleep(0)
    for indice, producto in enumerate(inventario):
        if producto["id"] == producto_id:
            producto_eliminado = inventario.pop(indice)
            return {
                "mensaje": "Producto eliminado correctamente",
                "producto": producto_eliminado,
            }

    raise HTTPException(
        status_code=404,
        detail="Producto no encontrado",
    )
