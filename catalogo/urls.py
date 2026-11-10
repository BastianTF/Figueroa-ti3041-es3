from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("", views.lista, name="lista_productos"),
    path("crear/", views.admin_producto_nuevo, name="crear_producto"),
    path("editar/<int:pk>/", views.editar_producto, name="editar_producto"),
    path("eliminar/<int:pk>/", views.eliminar_producto, name="eliminar_producto"),
    path("reportes/agregacion/", views.reporte_agregacion, name="reporte_agregacion"),
    path("reportes/filtrado/", views.reporte_filtrado, name="reporte_filtrado"),
    path("catalogo/", views.catalogo, name="catalogo"),
    path("contacto/", views.contacto_cliente, name="contacto"),
    path("ofertas/", views.ofertas, name="ofertas"),
    path("promociones/<slug:slug>/", views.promocion, name="promocion"),
    path("registro/", views.registro, name="registro"),
    path("login/", views.iniciar_sesion, name="login"),
    path("logout/", views.cerrar_sesion, name="logout"),
    path("comprar/<int:producto_id>/", views.comprar_producto, name="comprar"),
    path("producto/<int:producto_id>/", views.detalle, name="detalle"),
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/<int:producto_id>/", views.agregar_carrito, name="agregar_carrito"),
    path("carrito/quitar/<int:producto_id>/", views.quitar_del_carrito, name="quitar_carrito"),
    path("carrito/confirmar/", views.confirmar_carrito, name="confirmar_carrito"),
    path("administracion/", views.admin_panel, name="admin_panel"),
    path("administracion/productos/", views.admin_productos, name="admin_productos"),
    path("administracion/reportes/agregacion/", views.reporte_agregacion, name="admin_reporte_agregacion"),
    path("administracion/reportes/stock-critico/", views.reporte_filtrado, name="admin_reporte_filtrado"),
    path("administracion/productos/nuevo/", views.admin_producto_nuevo, name="admin_producto_nuevo"),
    path("administracion/productos/<int:producto_id>/editar/", views.admin_producto_editar, name="admin_producto_editar"),
    path("administracion/productos/<int:producto_id>/eliminar/", views.admin_producto_eliminar, name="admin_producto_eliminar"),
    path('contacto/', views.contacto_cliente, name='contacto_cliente'),
]