import pathlib
import numpy as np
import polars as pl

# resolve convierte la ruta en una completa sin atajos
# parent toma la carpeta que contiene el archivo
BASE_DIR = pathlib.Path(__file__).resolve().parent
RUTA_PRODUCTOS = BASE_DIR / "productos.csv"
RUTA_PARQUET = BASE_DIR / "ventas.parquet"

N_REGISTROS = 1_500_000
DIAS_HISTORIA = 365

rng = np.random.default_rng(42) #Semilla fija: siempre genera los mismos datos

#Leer el catalogo real
productos = pl.read_csv(RUTA_PRODUCTOS)
n_productos = productos.height

#Elegir un producto al azar para cada venta
indices = rng.integers(0, n_productos, size=N_REGISTROS)
nombres = productos["nombre"].to_numpy()[indices]
precios = productos["precio"].to_numpy()[indices]

cantidades = rng.integers(1, 6, size=N_REGISTROS)

#Fechas aleatorias del ultimo año
inicio = np.datetime64("2025-11-26T00:00")
minutos_aleatorios = rng.integers(0, DIAS_HISTORIA * 24 * 60, size=N_REGISTROS)
fechas = inicio + minutos_aleatorios.astype("timedelta64[m]")
fechas = fechas.astype("datetime64[us]")
fechas_texto = pl.Series(fechas).dt.strftime("%Y-%m-%d %H:%M")

#Tabla con el mismo esquema de ventas.csv
ventas = pl.DataFrame({
  "id_venta": np.arange(1, N_REGISTROS + 1), #Se usa numpy para la velocidad
  "fecha": fechas_texto,
  "producto": nombres,
  "precio": precios,
  "cantidad": cantidades,
}).with_columns(
  (pl.col("precio") * pl.col("cantidad")).round(2).alias("monto_total")
)

#Se guarda en formar parquet
ventas.write_parquet(RUTA_PARQUET)

print("Registros generados", ventas.height)
print("Esquema", ventas.schema)
print("Archivo", RUTA_PARQUET)