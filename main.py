import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    await asyncio.sleep(0)
    return inventario


# POST: agregar un nuevo producto
@app.post("/productos", status_code=201)
async def agregar_producto(producto: Producto):
    await asyncio.sleep(0)
    nuevo_producto = {
        "id": max((p["id"] for p in inventario), default=0) + 1,
        "nombre": producto.nombre.strip(),
        "precio": producto.precio,
        "cantidad": producto.cantidad,
    }

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
