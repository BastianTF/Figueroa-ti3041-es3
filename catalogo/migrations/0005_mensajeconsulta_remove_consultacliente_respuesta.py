import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrar_conversaciones_existentes(apps, schema_editor):
    ConsultaCliente = apps.get_model("catalogo", "ConsultaCliente")
    MensajeConsulta = apps.get_model("catalogo", "MensajeConsulta")
    base = schema_editor.connection.alias

    for consulta in ConsultaCliente.objects.using(base).iterator():
        MensajeConsulta.objects.using(base).create(
            consulta_id=consulta.pk,
            autor_id=consulta.usuario_id,
            remitente="cliente",
            contenido=consulta.mensaje,
            fecha=consulta.fecha,
        )
        if consulta.respuesta:
            MensajeConsulta.objects.using(base).create(
                consulta_id=consulta.pk,
                remitente="administrador",
                contenido=consulta.respuesta,
            )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalogo", "0004_consultacliente_usuario_respuesta"),
    ]

    operations = [
        migrations.CreateModel(
            name="MensajeConsulta",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "remitente",
                    models.CharField(
                        choices=[
                            ("cliente", "Cliente"),
                            ("administrador", "Administrador"),
                        ],
                        max_length=20,
                    ),
                ),
                ("contenido", models.TextField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                (
                    "autor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mensajes_consultas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "consulta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mensajes",
                        to="catalogo.consultacliente",
                    ),
                ),
            ],
            options={
                "ordering": ["fecha", "pk"],
            },
        ),
        migrations.RunPython(
            migrar_conversaciones_existentes,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="consultacliente",
            name="respuesta",
        ),
    ]
