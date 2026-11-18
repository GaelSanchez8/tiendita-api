import random
import uuid

from locust import HttpUser, between, task


class TiendaUser(HttpUser):
    """Simula las operaciones principales de un usuario de la tienda."""

    wait_time = between(1, 3)

    @task(5)
    def consultar_productos(self):
        self.client.get("/productos", name="GET /productos")

    @task(2)
    def comprobar_api(self):
        self.client.get("/", name="GET /")

    @task(1)
    def crear_y_eliminar_producto(self):
        producto = {
            "nombre": f"Producto de carga {uuid.uuid4().hex[:8]}",
            "precio": round(random.uniform(1, 100), 2),
            "cantidad": random.randint(1, 50),
        }

        with self.client.post(
            "/productos",
            json=producto,
            name="POST /productos",
            catch_response=True,
        ) as respuesta:
            if respuesta.status_code != 201:
                respuesta.failure(f"Respuesta inesperada: {respuesta.status_code}")
                return

            producto_creado = respuesta.json()

        self.client.delete(
            f"/productos/{producto_creado['id']}",
            name="DELETE /productos/{producto_id}",
        )