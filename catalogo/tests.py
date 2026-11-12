from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import ConsultaCliente, MensajeConsulta, Producto


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

	def test_inicio_muestra_resumen_y_enlaza_al_catalogo(self):
		respuesta = self.client.get(reverse("catalogo:lista"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(respuesta.context["total_productos"], 2)
		self.assertContains(respuesta, reverse("catalogo:catalogo"))
		self.assertNotContains(respuesta, "Taladro de prueba")
		self.assertNotContains(respuesta, "Martillo de prueba")

		respuesta_catalogo = self.client.get(reverse("catalogo:catalogo"))
		self.assertContains(respuesta_catalogo, "Taladro de prueba")
		self.assertContains(respuesta_catalogo, "Martillo de prueba")

	def test_contador_de_visitas_se_incrementa_en_la_sesion(self):
		respuesta = self.client.get(reverse("catalogo:lista_productos"))
		self.assertEqual(respuesta.context["visitas"], 1)

		respuesta = self.client.get(reverse("catalogo:lista_productos"))
		self.assertEqual(respuesta.context["visitas"], 2)

	def test_contacto_guarda_consulta_y_muestra_confirmacion(self):
		cliente = User.objects.create_user(
			username="cliente-contacto",
			password="test-password-123",
			email="cliente@example.com",
		)
		self.client.force_login(cliente)
		respuesta = self.client.post(
			reverse("catalogo:contacto"),
			{
				"mensaje": "Quisiera más información.",
				"producto_interes": self.producto.pk,
			},
		)

		self.assertEqual(respuesta.status_code, 200)
		self.assertTemplateUsed(respuesta, "catalogo/gracias.html")
		self.assertContains(respuesta, "Nos pondremos en contacto pronto")
		consulta = ConsultaCliente.objects.get()
		self.assertEqual(consulta.producto_interes, self.producto)
		self.assertEqual(consulta.usuario, cliente)
		self.assertEqual(consulta.nombre, cliente.username)
		self.assertEqual(consulta.correo, cliente.email)
		self.assertEqual(consulta.mensajes.count(), 1)
		self.assertEqual(consulta.mensajes.get().contenido, "Quisiera más información.")

	def test_contacto_no_guarda_consulta_invalida(self):
		cliente = User.objects.create_user(
			username="cliente-invalido",
			password="test-password-123",
			email="cliente@example.com",
		)
		self.client.force_login(cliente)
		respuesta = self.client.post(
			reverse("catalogo:contacto"),
			{
				"mensaje": "",
				"producto_interes": self.producto.pk,
			},
		)

		self.assertEqual(respuesta.status_code, 200)
		self.assertTemplateUsed(respuesta, "catalogo/contacto.html")
		self.assertEqual(ConsultaCliente.objects.count(), 0)

	def test_contacto_requiere_inicio_de_sesion(self):
		respuesta = self.client.get(reverse("catalogo:contacto"))

		self.assertRedirects(
			respuesta,
			f"{reverse('catalogo:login')}?next={reverse('catalogo:contacto')}",
		)

	def test_inicio_de_sesion_regresa_al_formulario_protegido(self):
		cliente = User.objects.create_user(
			username="cliente-login",
			password="test-password-123",
			email="cliente@example.com",
		)

		respuesta = self.client.post(
			reverse("catalogo:login"),
			{
				"username": cliente.username,
				"password": "test-password-123",
				"next": reverse("catalogo:contacto"),
			},
		)

		self.assertRedirects(respuesta, reverse("catalogo:contacto"))
		self.assertEqual(
			self.client.get(reverse("catalogo:contacto")).status_code,
			200,
		)

	def test_administrador_ve_consultas_en_contacto_en_lugar_del_formulario(self):
		ConsultaCliente.objects.create(
			nombre="Cliente de prueba",
			correo="cliente@example.com",
			mensaje="Consulta por disponibilidad.",
			producto_interes=self.producto,
		)
		administrador = User.objects.create_user(
			username="admin-consultas",
			password="test-password",
			is_staff=True,
		)
		self.client.force_login(administrador)

		respuesta = self.client.get(reverse("catalogo:contacto"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertTemplateUsed(respuesta, "catalogo/admin_consultas.html")
		self.assertContains(respuesta, "Cliente de prueba")
		self.assertContains(respuesta, "Consulta por disponibilidad.")
		self.assertContains(respuesta, self.producto.nombre)
		self.assertNotContains(respuesta, "Enviar Consulta")

	def test_pagina_de_ofertas_muestra_productos_con_descuento(self):
		respuesta = self.client.get(reverse("catalogo:ofertas"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Taladro de prueba")
		self.assertContains(respuesta, "-15%")
		self.assertContains(respuesta, "$33.992")

	def test_novedades_muestra_ocho_productos_mas_recientes(self):
		for numero in range(9):
			Producto.objects.create(
				nombre=f"Novedad {numero}",
				categoria="Herramientas",
				precio=1000 + numero,
				stock=1,
			)

		respuesta = self.client.get(reverse("catalogo:novedades"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(len(respuesta.context["productos"]), 8)
		self.assertEqual(
			list(respuesta.context["productos"].values_list("nombre", flat=True)),
			[f"Novedad {numero}" for numero in reversed(range(9))][:8],
		)
		self.assertContains(respuesta, "Explorar todo el catálogo")

	def test_pagina_de_servicios_enlaza_a_opciones_reales(self):
		respuesta = self.client.get(reverse("catalogo:servicios"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, reverse("catalogo:promocion", args=["cotiza"]))
		self.assertContains(respuesta, reverse("catalogo:contacto"))
		self.assertContains(respuesta, reverse("catalogo:login"))
		self.assertContains(respuesta, "Servicios para cada proyecto")

	def test_menu_principal_enlaza_a_novedades_y_servicios(self):
		respuesta = self.client.get(reverse("catalogo:lista"))

		self.assertContains(respuesta, reverse("catalogo:novedades"))
		self.assertContains(respuesta, reverse("catalogo:servicios"))
		self.assertContains(respuesta, 'class="cart-icon"')

	def test_tarjetas_de_inicio_enlazan_a_sus_paginas_promocionales(self):
		respuesta = self.client.get(reverse("catalogo:lista"))

		for slug in ("taller", "liquidacion", "calefaccion", "cotiza"):
			self.assertContains(
				respuesta,
				reverse("catalogo:promocion", args=[slug]),
			)

	def test_pagina_de_taller_muestra_herramientas_relevantes(self):
		respuesta = self.client.get(reverse("catalogo:promocion", args=["taller"]))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Taladro de prueba")
		self.assertContains(respuesta, "Martillo de prueba")

	def test_liquidacion_muestra_solo_descuentos_y_el_maximo_real(self):
		respuesta = self.client.get(reverse("catalogo:promocion", args=["liquidacion"]))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Taladro de prueba")
		self.assertContains(respuesta, "Descuentos de hasta")
		self.assertContains(respuesta, "15")
		self.assertNotContains(respuesta, "70%")

	def test_pagina_de_calefaccion_informa_si_no_hay_productos_publicados(self):
		respuesta = self.client.get(reverse("catalogo:promocion", args=["calefaccion"]))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Aún no hay calefactores publicados")
		self.assertContains(respuesta, "Consultar por calefacción")

	def test_pagina_de_cotizacion_guarda_consulta(self):
		cliente = User.objects.create_user(
			username="cliente-cotizacion",
			password="test-password-123",
			email="cotizacion@example.com",
		)
		self.client.force_login(cliente)
		respuesta = self.client.post(
			reverse("catalogo:promocion", args=["cotiza"]),
			{
				"mensaje": "Necesito cotizar herramientas para mi taller.",
				"producto_interes": self.producto.pk,
			},
		)

		self.assertEqual(respuesta.status_code, 200)
		self.assertTemplateUsed(respuesta, "catalogo/gracias.html")
		self.assertEqual(ConsultaCliente.objects.count(), 1)
		self.assertEqual(ConsultaCliente.objects.get().usuario, cliente)

	def test_pagina_de_cotizacion_requiere_inicio_de_sesion(self):
		respuesta = self.client.post(
			reverse("catalogo:promocion", args=["cotiza"]),
			{"mensaje": "Consulta anónima"},
		)

		self.assertRedirects(
			respuesta,
			f"{reverse('catalogo:login')}?next={reverse('catalogo:promocion', args=['cotiza'])}",
		)
		self.assertEqual(ConsultaCliente.objects.count(), 0)

	def test_promocion_desconocida_responde_404(self):
		respuesta = self.client.get(reverse("catalogo:promocion", args=["desconocida"]))

		self.assertEqual(respuesta.status_code, 404)

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

	def test_admin_puede_ver_consultas_de_clientes(self):
		ConsultaCliente.objects.create(
			nombre="Cliente de prueba",
			correo="cliente@example.com",
			mensaje="Necesito información sobre este producto.",
			producto_interes=self.producto,
		)

		respuesta = self.client.get(reverse("catalogo:admin_consultas"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Consultas de clientes")
		self.assertContains(respuesta, "Cliente de prueba")
		self.assertContains(respuesta, "cliente@example.com")
		self.assertContains(respuesta, "Necesito información sobre este producto.")
		self.assertContains(respuesta, self.producto.nombre)
		self.assertContains(
			self.client.get(reverse("catalogo:admin_panel")),
			reverse("catalogo:admin_consultas"),
		)

	def test_consultas_requieren_acceso_de_administrador(self):
		self.client.logout()

		respuesta = self.client.get(reverse("catalogo:admin_consultas"))

		self.assertRedirects(
			respuesta,
			f"{reverse('catalogo:login')}?next={reverse('catalogo:admin_consultas')}",
		)

	def test_administrador_puede_responder_una_consulta(self):
		consulta = ConsultaCliente.objects.create(
			nombre="Cliente de prueba",
			correo="cliente@example.com",
			mensaje="¿Está disponible?",
			producto_interes=self.producto,
		)

		respuesta = self.client.get(
			reverse("catalogo:admin_consulta_detalle", args=[consulta.pk])
		)
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Enviar respuesta")

		respuesta = self.client.post(
			reverse("catalogo:admin_consulta_detalle", args=[consulta.pk]),
			{"contenido": "Sí, está disponible."},
		)

		self.assertRedirects(
			respuesta,
			reverse("catalogo:admin_consulta_detalle", args=[consulta.pk]),
		)
		consulta.refresh_from_db()
		self.assertEqual(consulta.mensajes.count(), 1)
		mensaje = consulta.mensajes.get()
		self.assertEqual(mensaje.contenido, "Sí, está disponible.")
		self.assertEqual(mensaje.remitente, MensajeConsulta.Remitente.ADMINISTRADOR)

	def test_cliente_solo_ve_sus_consultas_y_respuestas(self):
		cliente = User.objects.create_user(
			username="cliente-consultas",
			password="test-password-123",
			email="cliente@example.com",
		)
		consulta_cliente = ConsultaCliente.objects.create(
			nombre=cliente.username,
			correo=cliente.email,
			mensaje="Mi consulta",
			usuario=cliente,
		)
		MensajeConsulta.objects.create(
			consulta=consulta_cliente,
			autor=cliente,
			remitente=MensajeConsulta.Remitente.CLIENTE,
			contenido="Mi consulta",
		)
		MensajeConsulta.objects.create(
			consulta=consulta_cliente,
			remitente=MensajeConsulta.Remitente.ADMINISTRADOR,
			contenido="Mi respuesta",
		)
		ConsultaCliente.objects.create(
			nombre="Otro cliente",
			correo="otro@example.com",
			mensaje="Consulta privada",
		)
		self.client.force_login(cliente)

		respuesta = self.client.get(reverse("catalogo:mis_consultas"))

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Mi consulta")
		self.assertNotContains(respuesta, "Consulta privada")

		respuesta = self.client.get(
			reverse("catalogo:cliente_consulta_detalle", args=[consulta_cliente.pk])
		)
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, "Mi consulta")
		self.assertContains(respuesta, "Mi respuesta")
		self.assertContains(respuesta, "chat-message--admin")

	def test_cliente_puede_responder_en_el_chat_y_no_acceder_a_otro(self):
		cliente = User.objects.create_user(
			username="cliente-chat",
			password="test-password-123",
			email="chat@example.com",
		)
		otra_cuenta = User.objects.create_user(
			username="otro-chat",
			password="test-password-123",
			email="otro@example.com",
		)
		consulta = ConsultaCliente.objects.create(
			nombre=cliente.username,
			correo=cliente.email,
			mensaje="Tengo una duda.",
			usuario=cliente,
		)
		self.client.force_login(cliente)

		respuesta = self.client.post(
			reverse("catalogo:cliente_consulta_detalle", args=[consulta.pk]),
			{"contenido": "¿Me pueden ayudar?"},
		)

		self.assertRedirects(
			respuesta,
			reverse("catalogo:cliente_consulta_detalle", args=[consulta.pk]),
		)
		mensaje = consulta.mensajes.get()
		self.assertEqual(mensaje.remitente, MensajeConsulta.Remitente.CLIENTE)
		self.assertEqual(mensaje.autor, cliente)

		consulta.usuario = otra_cuenta
		consulta.save(update_fields=["usuario"])
		respuesta = self.client.get(
			reverse("catalogo:cliente_consulta_detalle", args=[consulta.pk])
		)
		self.assertEqual(respuesta.status_code, 404)

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


class ConsultaClienteTests(TestCase):
	def test_consulta_se_guarda_y_conserva_si_se_elimina_el_producto(self):
		producto = Producto.objects.create(
			nombre="Producto consultado",
			categoria="Herramientas",
			precio=12000,
			stock=2,
		)
		consulta = ConsultaCliente.objects.create(
			nombre="Cliente de prueba",
			correo="cliente@example.com",
			mensaje="¿Está disponible?",
			producto_interes=producto,
		)

		self.assertEqual(str(consulta), "Cliente de prueba - cliente@example.com")
		self.assertIsNotNone(consulta.fecha)

		producto.delete()
		consulta.refresh_from_db()
		self.assertIsNone(consulta.producto_interes)
