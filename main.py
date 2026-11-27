from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from datetime import datetime
import asyncio
import polars as pl
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

ESQUEMA_VENTAS = {
    "id_venta": pl.Int64,
    "fecha": pl.String,
    "producto": pl.String,
    "precio": pl.Float64,
    "cantidad": pl.Float64,
    "monto_total": pl.Float64,
}

scheduler = AsyncIOScheduler()
lock = asyncio.Lock()  # Lock para manejar la concurrencia en operaciones de escritura

""" Esto es para que el corte de caja se ejecute solo sin tener que llamarlo mientras el servidor
puede seguir atendiendo servidores  """

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(corte_de_caja, "interval", minutes=2, id="corte_de_caja")
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="API de LUNIX", lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
RUTA_PARQUET = BASE_DIR / "ventas.parquet"
RUTA_PRODUCTOS = BASE_DIR / "productos.csv"
RUTA_VENTAS = BASE_DIR / "ventas.csv"


#Cargar el archivo de ventas y cambiar el tipo de cada columna del csv 
#para que coincida con el del Parquet
def leer_ventas_csv():
    return pl.scan_csv(RUTA_VENTAS).with_columns(
        pl.col("id_venta").cast(pl.Int64),
        pl.col("fecha").cast(pl.String),
        pl.col("producto").cast(pl.String),
        pl.col("precio").cast(pl.Float64),
        pl.col("cantidad").cast(pl.Int64),
        pl.col("monto_total").cast(pl.Float64),
            
    )

def cargar_ventas():
    historico = pl.scan_parquet(RUTA_PARQUET)
    return pl.concat([historico, leer_ventas_csv()])


async def corte_de_caja():
    async with lock:
        recientes = leer_ventas_csv().collect()

        if recientes.height == 0:
            return

        historico = pl.read_parquet(RUTA_PARQUET)
        pl.concat([historico, recientes]).write_parquet(RUTA_PARQUET)

        #vacia ventas.csv dejando solo el encabezado
        recientes.clear().write_csv(RUTA_VENTAS)


#endpoint para probar la funcion de cargar ventas
@app.get("/api/analisis/kpis")
async def kpis_polars():
    ventas = cargar_ventas().collect()

    if ventas.height == 0:
        return {
            "producto_estrella": None,
            "ingresos_totales": 0,
            "transacciones": 0,
            "ticket_promedio": 0,
        }
    producto_estrella = (
        ventas.group_by("producto")
        .agg(pl.col("cantidad").sum().alias("unidades"))
        .sort("unidades", descending=True)
        .row(0)[0]
    )
    ingresos = round(ventas["monto_total"].sum(), 2)
    transacciones = ventas.height

    return {
        "producto_estrella": producto_estrella,
        "ingresos_totales": ingresos,
        "transacciones": transacciones,
        "ticket_promedio": round(ingresos / transacciones, 2)
    }


#Endpoint de los productos mas vendidos
@app.get("/api/analisis/mas-vendidos")
async def mas_vendidas():
    ventas = cargar_ventas().collect()

    if ventas.height == 0:
        return[]

    resultado = (
        ventas.group_by("producto")
        .agg(
            pl.col("cantidad").sum().alias("unidades"),
            pl.col("monto_total").sum().round(2).alias("monto_total"),
        )
        .sort("unidades", descending=True)
    )
    return resultado.to_dicts()


@app.get("/api/analisis/ventas-por-fecha")
async def ventas_por_fecha_polars():
    ventas = cargar_ventas().collect()

    if ventas.height == 0:
        return[]

    resultado = (
        ventas.with_columns(pl.col("fecha").str.slice(0, 10).alias("dia")) #toma los primero 10 caracteres de la fecha
        .group_by("dia")
        .agg(pl.col("monto_total").sum().round(2).alias("monto_total"))
        .sort("dia") #ordena la fecha de la mas antigua a la mas reciente
    )
    return resultado.to_dicts()


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