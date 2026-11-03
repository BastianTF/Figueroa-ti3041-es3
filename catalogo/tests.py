from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Producto


class CatalogoTests(TestCase):
	def setUp(self):
		self.producto = Producto.objects.create(
			nombre="Taladro de prueba",
			categoria="Herramientas eléctricas",
			precio=39990,
			stock=8,
			imagen="https://example.com/taladro.jpg",
			caracteristicas=["Potencia: 650 W"],
			descuento=15,
			precio_oferta=33992,
		)
		Producto.objects.create(
			nombre="Martillo de prueba",
			categoria="Herramientas manuales",
			precio=7990,
			stock=24,
			imagen="https://example.com/martillo.jpg",
			caracteristicas=["Peso: 16 oz"],
		)

	def test_inicio_lista_productos_desde_la_base_de_datos(self):
		respuesta = self.client.get(reverse("catalogo:lista"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Taladro de prueba")
		self.assertContains(respuesta, "Martillo de prueba")
		self.assertEqual(respuesta.context["total_productos"], 2)

	def test_pagina_de_ofertas_muestra_productos_con_descuento(self):
		respuesta = self.client.get(reverse("catalogo:ofertas"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Taladro de prueba")
		self.assertContains(respuesta, "-15%")
		self.assertContains(respuesta, "$33.992")

	def test_filtra_por_categoria_y_ordena_por_precio(self):
		categoria = self.producto.categoria

		respuesta = self.client.get(reverse("catalogo:catalogo"), {"categoria": categoria})
		self.assertEqual(respuesta.status_code, 200)
		self.assertTrue(all(producto.categoria == categoria for producto in respuesta.context["productos"]))

		respuesta = self.client.get(reverse("catalogo:catalogo"), {"orden": "precio_asc"})
		precios = [producto.precio for producto in respuesta.context["productos"]]
		self.assertEqual(precios, sorted(precios))

	def test_contador_aumenta_y_se_descuenta_al_quitar(self):
		self.client.post(reverse("catalogo:agregar_carrito", args=[self.producto.pk]))
		respuesta = self.client.get(reverse("catalogo:lista"))
		self.assertContains(respuesta, 'class="cart-badge">1</span>')

		self.client.get(reverse("catalogo:quitar_carrito", args=[self.producto.pk]))
		respuesta = self.client.get(reverse("catalogo:lista"))
		self.assertNotContains(respuesta, "cart-badge")

	def test_comando_puebla_catalogo_completo_y_es_repetible(self):
		call_command("poblar_productos", stdout=StringIO())
		self.assertEqual(Producto.objects.count(), 40)
		self.assertEqual(Producto.objects.filter(descuento__gt=0).count(), 4)

		call_command("poblar_productos", stdout=StringIO())
		self.assertEqual(Producto.objects.count(), 40)

	def test_producto_se_muestra_en_el_admin_de_django(self):
		call_command("poblar_productos", stdout=StringIO())
		administrador = User.objects.create_superuser(
			username="admin-prueba",
			password="prueba-segura",
			email="admin@example.com",
		)
		self.client.force_login(administrador)

		respuesta = self.client.get("/admin/catalogo/producto/")

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Taladro percutor 650W")


class AdministracionProductosTests(TestCase):
	def setUp(self):
		self.administrador = User.objects.create_user(
			username="admin-productos",
			password="clave-prueba",
			is_staff=True,
		)
		self.client.force_login(self.administrador)
		self.producto = Producto.objects.create(
			nombre="Producto existente",
			categoria="Herramientas",
			precio=15000,
			stock=3,
			caracteristicas=["Durable"],
		)

	def test_rutas_crud_compatibles(self):
		self.assertEqual(reverse("catalogo:lista_productos"), "/")
		self.assertEqual(reverse("catalogo:crear_producto"), "/crear/")
		self.assertEqual(
			reverse("catalogo:editar_producto", args=[self.producto.pk]),
			f"/editar/{self.producto.pk}/",
		)
		self.assertEqual(
			reverse("catalogo:eliminar_producto", args=[self.producto.pk]),
			f"/eliminar/{self.producto.pk}/",
		)

	def test_reporte_agregacion_resume_productos_por_categoria(self):
		Producto.objects.create(
			nombre="Otra herramienta",
			categoria="Herramientas",
			precio=25000,
			stock=4,
		)

		respuesta = self.client.get(reverse("catalogo:reporte_agregacion"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Reporte 1: Resumen por Categoría (Agregación ORM)")
		fila = respuesta.context["reporte"].get(categoria="Herramientas")
		self.assertEqual(fila["total_productos"], 2)
		self.assertEqual(fila["promedio_precio"], 20000)
		self.assertEqual(fila["stock_total"], 7)

	def test_reporte_filtrado_muestra_solo_stock_menor_a_cinco(self):
		Producto.objects.create(
			nombre="Stock límite",
			categoria="Herramientas",
			precio=1000,
			stock=5,
		)

		respuesta = self.client.get(reverse("catalogo:reporte_filtrado"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Producto existente")
		self.assertNotContains(respuesta, "Stock límite")
		self.assertEqual(
			list(respuesta.context["productos"].values_list("pk", flat=True)),
			[self.producto.pk],
		)

	def test_reportes_requieren_acceso_de_administrador(self):
		self.client.logout()

		for nombre_ruta in ("reporte_agregacion", "reporte_filtrado"):
			with self.subTest(reporte=nombre_ruta):
				respuesta = self.client.get(reverse(f"catalogo:{nombre_ruta}"))
				self.assertEqual(respuesta.status_code, 302)
				self.assertTrue(respuesta.url.startswith(reverse("catalogo:login")))

	def test_crear_producto_con_formulario(self):
		respuesta = self.client.post(
			reverse("catalogo:admin_producto_nuevo"),
			{
				"nombre": "Producto nuevo",
				"categoria": "Jardín",
				"precio": 12000,
				"stock": 5,
				"imagen": "",
				"caracteristicas": "Resistente\nLiviano",
			},
		)

		self.assertRedirects(respuesta, reverse("catalogo:admin_productos"))
		producto = Producto.objects.get(nombre="Producto nuevo")
		self.assertEqual(producto.caracteristicas, ["Resistente", "Liviano"])

	def test_editar_producto_conserva_y_actualiza_campos(self):
		respuesta = self.client.post(
			reverse("catalogo:admin_producto_editar", args=[self.producto.pk]),
			{
				"nombre": "Producto actualizado",
				"categoria": "Construcción",
				"precio": 17000,
				"stock": 7,
				"imagen": "https://example.com/producto.jpg",
				"caracteristicas": "Nuevo detalle",
			},
		)

		self.assertRedirects(respuesta, reverse("catalogo:admin_productos"))
		self.producto.refresh_from_db()
		self.assertEqual(self.producto.nombre, "Producto actualizado")
		self.assertEqual(self.producto.caracteristicas, ["Nuevo detalle"])
		self.assertEqual(self.producto.imagen, "https://example.com/producto.jpg")

	def test_eliminar_producto_solicita_confirmacion_y_elimina_por_post(self):
		url = reverse("catalogo:admin_producto_eliminar", args=[self.producto.pk])

		respuesta = self.client.get(url)
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "¿Estás seguro")
		self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

		respuesta = self.client.post(url)
		self.assertRedirects(respuesta, reverse("catalogo:admin_productos"))
		self.assertFalse(Producto.objects.filter(pk=self.producto.pk).exists())

	def test_usuario_no_administrador_no_puede_administrar_productos(self):
		self.client.logout()

		respuesta = self.client.get(reverse("catalogo:admin_producto_nuevo"))

		self.assertRedirects(
			respuesta,
			f"{reverse('catalogo:login')}?next={reverse('catalogo:admin_producto_nuevo')}",
		)
