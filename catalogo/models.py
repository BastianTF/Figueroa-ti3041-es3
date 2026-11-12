from django.db import models
from django.contrib.auth.models import User

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    precio = models.IntegerField()
    stock = models.IntegerField()
    imagen = models.URLField(max_length=500, blank=True)
    caracteristicas = models.JSONField(default=list, blank=True)
    descuento = models.PositiveSmallIntegerField(null=True, blank=True)
    precio_oferta = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"


class ConsultaCliente(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    mensaje = models.TextField()
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultas_cliente",
    )
    producto_interes = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.correo}"


class MensajeConsulta(models.Model):
    class Remitente(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        ADMINISTRADOR = "administrador", "Administrador"

    consulta = models.ForeignKey(
        ConsultaCliente,
        on_delete=models.CASCADE,
        related_name="mensajes",
    )
    autor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensajes_consultas",
    )
    remitente = models.CharField(max_length=20, choices=Remitente.choices)
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.get_remitente_display()} - consulta {self.consulta_id}"