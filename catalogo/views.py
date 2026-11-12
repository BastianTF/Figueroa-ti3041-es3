import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg, Count, Exists, Max, OuterRef, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ConsultaClienteForm, MensajeConsultaForm, ProductoForm
from .models import ConsultaCliente, MensajeConsulta, Producto

VENTAS_PATH = Path(__file__).resolve().parent / "data" / "ventas.json"

def cargar_ventas():
    if not VENTAS_PATH.exists():
        return []
    with open(VENTAS_PATH, encoding="utf-8-sig") as archivo:
        return json.load(archivo)


def guardar_ventas(ventas):
    with open(VENTAS_PATH, "w", encoding="utf-8") as archivo:
        json.dump(ventas, archivo, ensure_ascii=False, indent=2)


def _es_administrador(user):
    return user.is_authenticated and user.is_staff


def _url_siguiente_segura(request, url):
    if url and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return ""


def _guardar_consulta_cliente(form, usuario):
    with transaction.atomic():
        consulta = form.save(commit=False)
        consulta.usuario = usuario
        consulta.nombre = (usuario.get_full_name().strip() or usuario.get_username())[:100]
        consulta.correo = usuario.email
        consulta.save()
        MensajeConsulta.objects.create(
            consulta=consulta,
            autor=usuario,
            remitente=MensajeConsulta.Remitente.CLIENTE,
            contenido=consulta.mensaje,
        )
    return consulta


PROMOCIONES = {
    "taller": {
        "eyebrow": "Selección para profesionales y aficionados",
        "title": "Herramientas para llevar tu taller más lejos",
        "description": "Encuentra herramientas manuales, eléctricas y de medición para reparar, construir y dar vida a tus proyectos.",
        "categories": ("Herramientas manuales", "Herramientas eléctricas", "Medición"),
        "features": (
            ("01", "Herramientas manuales", "Esenciales confiables para ajustes, montaje y reparación."),
            ("02", "Potencia eléctrica", "Equipos para avanzar con precisión en cada proyecto."),
            ("03", "Medición precisa", "Prepara cada trabajo con medidas y nivelación confiables."),
        ),
        "empty_message": "Estamos preparando esta selección. Revisa el catálogo completo para encontrar más alternativas.",
        "cta": "Explorar catálogo",
    },
    "liquidacion": {
        "eyebrow": "Precios especiales en productos seleccionados",
        "title": "Aprovecha las ofertas disponibles",
        "description": "Revisa los productos con descuento vigente. El precio y la disponibilidad se actualizan desde nuestro catálogo.",
        "features": (
            ("01", "Descuentos visibles", "Cada producto muestra su precio anterior y su precio de oferta."),
            ("02", "Stock actualizado", "Consulta las unidades disponibles antes de comprar."),
            ("03", "Compra fácil", "Agrega tus favoritos al carro o revisa sus detalles."),
        ),
        "empty_message": "Por ahora no hay productos en liquidación. Vuelve pronto para revisar nuevas ofertas.",
        "cta": "Ver todos los productos",
    },
    "calefaccion": {
        "eyebrow": "Recomendados para tu hogar",
        "title": "Prepárate para los días fríos",
        "description": "Estamos preparando nuestra selección de calefacción. Cuéntanos qué necesitas y te ayudaremos a encontrar una alternativa.",
        "search": "calefac",
        "features": (
            ("01", "Elige para tu espacio", "Cuéntanos qué ambiente quieres calefaccionar."),
            ("02", "Consulta disponibilidad", "Solicita información antes de decidir tu compra."),
            ("03", "Atención personalizada", "Déjanos tus datos y responderemos tu consulta."),
        ),
        "empty_message": "Aún no hay calefactores publicados en el catálogo en línea. Puedes consultar disponibilidad mediante el formulario.",
        "cta": "Consultar disponibilidad",
    },
    "cotiza": {
        "eyebrow": "Atención personalizada",
        "title": "Cotiza los productos para tu proyecto",
        "description": "Cuéntanos qué materiales o herramientas estás buscando. Envíanos tu consulta y nos pondremos en contacto contigo.",
        "features": (
            ("01", "Cuéntanos tu proyecto", "Indica los productos o materiales que necesitas."),
            ("02", "Incluye los detalles", "Puedes mencionar cantidades, medidas o características."),
            ("03", "Recibe atención", "Nuestro equipo recibirá tu solicitud para responderte."),
        ),
        "cta": "Ver catálogo",
    },
}


def lista(request):
    visitas = request.session.get("contador_visitas", 0) + 1
    request.session["contador_visitas"] = visitas

    productos = Producto.objects.order_by("id")
    total_productos = productos.count()
    total_con_stock = productos.filter(stock__gt=0).count()

    contexto = {
        "productos": productos,
        "total_productos": total_productos,
        "total_con_stock": total_con_stock,
        "total_sin_stock": total_productos - total_con_stock,
        "visitas": visitas,
        "max_descuento": Producto.objects.filter(
            descuento__gt=0,
            precio_oferta__isnull=False,
        ).aggregate(max_descuento=Max("descuento"))["max_descuento"] or 0,
    }
    return render(request, "catalogo/lista.html", contexto)


def contacto_cliente(request):
    if request.user.is_authenticated and request.user.is_staff:
        consultas = ConsultaCliente.objects.select_related("producto_interes").order_by("-fecha")
        return render(request, "catalogo/admin_consultas.html", {"consultas": consultas})

    if not request.user.is_authenticated:
        return redirect_to_login(
            request.get_full_path(),
            login_url=reverse("catalogo:login"),
        )

    form = ConsultaClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        _guardar_consulta_cliente(form, request.user)
        return render(
            request,
            "catalogo/gracias.html",
            {"mensaje": "¡Gracias por tu consulta! Nos pondremos en contacto pronto."},
        )
    return render(request, "catalogo/contacto.html", {"form": form})


def ofertas(request):
    productos = Producto.objects.filter(
        descuento__gt=0,
        precio_oferta__isnull=False,
    ).order_by("id")
    return render(request, "catalogo/ofertas.html", {"productos": productos})


def novedades(request):
    productos = Producto.objects.order_by("-id")[:8]
    return render(request, "catalogo/novedades.html", {"productos": productos})


def servicios(request):
    return render(request, "catalogo/servicios.html")


def promocion(request, slug):
    campana = PROMOCIONES.get(slug)
    if campana is None:
        raise Http404("La promoción solicitada no existe.")

    if slug == "cotiza" and not request.user.is_authenticated:
        return redirect_to_login(
            request.get_full_path(),
            login_url=reverse("catalogo:login"),
        )

    productos = Producto.objects.all()
    if slug == "taller":
        productos = productos.filter(categoria__in=campana["categories"])
    elif slug == "liquidacion":
        productos = productos.filter(descuento__gt=0, precio_oferta__isnull=False)
    elif slug == "calefaccion":
        productos = productos.filter(
            Q(nombre__icontains=campana["search"])
            | Q(categoria__icontains=campana["search"])
        )
    else:
        productos = Producto.objects.none()

    productos = productos.order_by(
        "-descuento" if slug == "liquidacion" else "nombre",
        "nombre",
    )
    form = ConsultaClienteForm(request.POST or None) if slug == "cotiza" else None
    if form and request.method == "POST" and form.is_valid():
        _guardar_consulta_cliente(form, request.user)
        return render(
            request,
            "catalogo/gracias.html",
            {"mensaje": "¡Gracias por tu consulta! Nos pondremos en contacto pronto."},
        )

    max_descuento = productos.aggregate(max_descuento=Max("descuento"))["max_descuento"] or 0
    return render(
        request,
        "catalogo/promocion.html",
        {
            "campana": campana,
            "slug": slug,
            "productos": productos,
            "form": form,
            "max_descuento": max_descuento,
        },
    )


def catalogo(request):
    query = (request.GET.get("q") or "").strip()
    categoria = (request.GET.get("categoria") or "").strip()
    orden = request.GET.get("orden") or ""
    precio_minimo = request.GET.get("precio_minimo") or ""
    precio_maximo = request.GET.get("precio_maximo") or ""
    productos = Producto.objects.all()
    categorias = Producto.objects.order_by("categoria").values_list("categoria", flat=True).distinct()

    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(categoria__icontains=query))

    if categoria:
        productos = productos.filter(categoria=categoria)

    try:
        if precio_minimo:
            productos = productos.filter(precio__gte=int(precio_minimo))
    except ValueError:
        precio_minimo = ""

    try:
        if precio_maximo:
            productos = productos.filter(precio__lte=int(precio_maximo))
    except ValueError:
        precio_maximo = ""

    ordenes = {
        "precio_asc": "precio",
        "precio_desc": "-precio",
        "nombre": "nombre",
    }
    if orden in ordenes:
        productos = productos.order_by(ordenes[orden])

    total_productos = productos.count()
    total_con_stock = productos.filter(stock__gt=0).count()

    contexto = {
        "productos": productos,
        "query": query,
        "categoria": categoria,
        "categorias": categorias,
        "orden": orden,
        "precio_minimo": precio_minimo,
        "precio_maximo": precio_maximo,
        "total_productos": total_productos,
        "total_con_stock": total_con_stock,
        "total_sin_stock": total_productos - total_con_stock,
    }
    return render(request, "catalogo/catalogo.html", contexto)


def detalle(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    return render(request, "catalogo/detalle.html", {"producto": producto})


def _obtener_carrito(request):
    return {str(producto_id): int(cantidad) for producto_id, cantidad in request.session.get("carrito", {}).items()}


def _guardar_carrito(request, carrito):
    request.session["carrito"] = carrito
    request.session.modified = True


def _datos_carrito(request):
    carrito = _obtener_carrito(request)
    items = []
    total = 0
    productos = Producto.objects.in_bulk(
        int(producto_id) for producto_id in carrito
    )

    for producto_id, cantidad in carrito.items():
        producto = productos.get(int(producto_id))
        if producto is None or cantidad <= 0:
            continue
        subtotal = producto.precio * cantidad
        items.append({"producto": producto, "cantidad": cantidad, "subtotal": subtotal})
        total += subtotal

    return items, total


def agregar_carrito(request, producto_id):
    if request.method != "POST":
        return redirect("catalogo:detalle", producto_id=producto_id)

    if request.user.is_staff:
        messages.error(request, "Los administradores no pueden comprar productos.")
        return redirect("catalogo:detalle", producto_id=producto_id)

    producto = get_object_or_404(Producto, pk=producto_id)

    carrito = _obtener_carrito(request)
    cantidad_actual = carrito.get(str(producto_id), 0)
    if cantidad_actual >= producto.stock:
        messages.error(request, "No puedes agregar más unidades que el stock disponible.")
    else:
        carrito[str(producto_id)] = cantidad_actual + 1
        _guardar_carrito(request, carrito)
        messages.success(request, f"{producto.nombre} se agregó al carrito.")

    return redirect("catalogo:carrito")


def carrito(request):
    items, total = _datos_carrito(request)
    return render(request, "catalogo/carrito.html", {"items": items, "total": total})


def quitar_del_carrito(request, producto_id):
    carrito = _obtener_carrito(request)
    carrito.pop(str(producto_id), None)
    _guardar_carrito(request, carrito)
    return redirect("catalogo:carrito")


@login_required(login_url="catalogo:login")
def confirmar_carrito(request):
    if request.user.is_staff:
        messages.error(request, "Los administradores no pueden comprar productos.")
        return redirect("catalogo:carrito")

    if request.method != "POST":
        return redirect("catalogo:carrito")

    items, _ = _datos_carrito(request)
    if not items:
        messages.error(request, "Tu carrito está vacío.")
        return redirect("catalogo:carrito")

    carrito = _obtener_carrito(request)
    with transaction.atomic():
        productos = Producto.objects.select_for_update().in_bulk(
            int(producto_id) for producto_id in carrito
        )
        for producto_id, cantidad in carrito.items():
            producto = productos.get(int(producto_id))
            if producto is None or cantidad > producto.stock:
                messages.error(request, "Uno de los productos ya no tiene stock suficiente.")
                return redirect("catalogo:carrito")

        for producto_id, cantidad in carrito.items():
            producto = productos[int(producto_id)]
            producto.stock -= cantidad
            producto.save(update_fields=("stock",))

    ventas = cargar_ventas()
    ventas.append({
        "id": len(ventas) + 1,
        "usuario": request.user.username,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": sum(item["subtotal"] for item in items),
        "productos": [
            {"id": item["producto"].id, "nombre": item["producto"].nombre, "cantidad": item["cantidad"], "subtotal": item["subtotal"]}
            for item in items
        ],
    })
    guardar_ventas(ventas)
    _guardar_carrito(request, {})
    messages.success(request, "Compra confirmada correctamente.")
    return redirect("catalogo:lista")


def registro(request):
    next_url = _url_siguiente_segura(
        request,
        request.POST.get("next") or request.GET.get("next"),
    )
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        password2 = request.POST.get("password2") or ""

        if not username or not password or not email:
            messages.error(request, "Debes completar todos los campos.")
            return render(request, "catalogo/registro.html", {"next_url": next_url})

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "catalogo/registro.html", {"next_url": next_url})

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ese nombre de usuario ya existe.")
            return render(request, "catalogo/registro.html", {"next_url": next_url})

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Cuenta creada correctamente.")
        if next_url:
            return redirect(f"{reverse('catalogo:login')}?{urlencode({'next': next_url})}")
        return redirect("catalogo:login")

    return render(request, "catalogo/registro.html", {"next_url": next_url})


def iniciar_sesion(request):
    next_url = _url_siguiente_segura(
        request,
        request.POST.get("next") or request.GET.get("next"),
    )
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if next_url:
                return redirect(next_url)
            return redirect("catalogo:lista")

        messages.error(request, "Credenciales inválidas.")

    return render(request, "catalogo/login.html", {"next_url": next_url})


def cerrar_sesion(request):
    logout(request)
    return redirect("catalogo:lista")


@login_required(login_url="catalogo:login")
def comprar_producto(request, producto_id):
    return agregar_carrito(request, producto_id)


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_panel(request):
    productos = Producto.objects.all()
    ventas = cargar_ventas()
    contexto = {
        "productos": productos,
        "ventas": ventas,
        "total_productos": productos.count(),
        "stock_total": sum(producto.stock for producto in productos),
        "ventas_total": sum(venta["total"] for venta in ventas),
    }
    return render(request, "catalogo/admin_panel.html", contexto)


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_consultas(request):
    respuesta_admin = MensajeConsulta.objects.filter(
        consulta_id=OuterRef("pk"),
        remitente=MensajeConsulta.Remitente.ADMINISTRADOR,
    )
    consultas = ConsultaCliente.objects.select_related("producto_interes").annotate(
        respondida=Exists(respuesta_admin),
    ).order_by("-fecha")
    return render(request, "catalogo/admin_consultas.html", {"consultas": consultas})


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_consulta_detalle(request, consulta_id):
    consulta = get_object_or_404(
        ConsultaCliente.objects.select_related("producto_interes", "usuario"),
        pk=consulta_id,
    )
    form = MensajeConsultaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        mensaje = form.save(commit=False)
        mensaje.consulta = consulta
        mensaje.autor = request.user
        mensaje.remitente = MensajeConsulta.Remitente.ADMINISTRADOR
        mensaje.save()
        messages.success(request, "El mensaje se envió correctamente.")
        return redirect("catalogo:admin_consulta_detalle", consulta_id=consulta.pk)

    return render(
        request,
        "catalogo/admin_consulta_detalle.html",
        {
            "consulta": consulta,
            "form": form,
            "mensajes": consulta.mensajes.select_related("autor").all(),
            "es_administrador": True,
        },
    )


@login_required(login_url="catalogo:login")
def mis_consultas(request):
    if request.user.is_staff:
        return redirect("catalogo:admin_consultas")

    respuesta_admin = MensajeConsulta.objects.filter(
        consulta_id=OuterRef("pk"),
        remitente=MensajeConsulta.Remitente.ADMINISTRADOR,
    )
    consultas = ConsultaCliente.objects.filter(usuario=request.user).select_related(
        "producto_interes"
    ).annotate(respondida=Exists(respuesta_admin)).order_by("-fecha")
    return render(request, "catalogo/mis_consultas.html", {"consultas": consultas})


@login_required(login_url="catalogo:login")
def cliente_consulta_detalle(request, consulta_id):
    if request.user.is_staff:
        return redirect("catalogo:admin_consultas")

    consulta = get_object_or_404(
        ConsultaCliente.objects.select_related("producto_interes"),
        pk=consulta_id,
        usuario=request.user,
    )
    form = MensajeConsultaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        mensaje = form.save(commit=False)
        mensaje.consulta = consulta
        mensaje.autor = request.user
        mensaje.remitente = MensajeConsulta.Remitente.CLIENTE
        mensaje.save()
        messages.success(request, "Tu mensaje se envió correctamente.")
        return redirect("catalogo:cliente_consulta_detalle", consulta_id=consulta.pk)

    return render(
        request,
        "catalogo/cliente_consulta_detalle.html",
        {
            "consulta": consulta,
            "form": form,
            "mensajes": consulta.mensajes.select_related("autor").all(),
            "es_administrador": False,
        },
    )


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_producto_nuevo(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Producto creado correctamente.")
        return redirect("catalogo:admin_productos")

    return render(
        request,
        "catalogo/form_producto.html",
        {"form": form, "titulo": "Crear Producto"},
    )


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_producto_editar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Producto actualizado correctamente.")
        return redirect("catalogo:admin_productos")

    return render(
        request,
        "catalogo/form_producto.html",
        {"form": form, "titulo": f"Editar Producto: {producto.nombre}"},
    )


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_producto_eliminar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    if request.method == "POST":
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")
        return redirect("catalogo:admin_productos")

    return render(
        request,
        "catalogo/confirmar_eliminacion.html",
        {"producto": producto},
    )


@user_passes_test(_es_administrador, login_url="catalogo:login")
def admin_productos(request):
    return render(
        request,
        "catalogo/admin_productos.html",
        {"productos": Producto.objects.order_by("id")},
    )


@user_passes_test(_es_administrador, login_url="catalogo:login")
def reporte_agregacion(request):
    reporte = Producto.objects.values("categoria").annotate(
        total_productos=Count("id"),
        promedio_precio=Avg("precio"),
        stock_total=Sum("stock"),
    ).order_by("categoria")
    return render(request, "catalogo/reporte_agregacion.html", {"reporte": reporte})


@user_passes_test(_es_administrador, login_url="catalogo:login")
def reporte_filtrado(request):
    productos_criticos = Producto.objects.filter(stock__lt=5).order_by("stock", "id")
    return render(
        request,
        "catalogo/reporte_filtrado.html",
        {"productos": productos_criticos},
    )


def editar_producto(request, pk):
    return admin_producto_editar(request, producto_id=pk)


def eliminar_producto(request, pk):
    return admin_producto_eliminar(request, producto_id=pk)
