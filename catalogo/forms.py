from django import forms

from .models import ConsultaCliente, MensajeConsulta, Producto


class ProductoForm(forms.ModelForm):
    caracteristicas = forms.CharField(
        required=False,
        label="Características, una por línea",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
    )

    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "precio", "stock", "imagen", "caracteristicas"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.TextInput(attrs={"class": "form-control"}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "imagen": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["caracteristicas"].initial = "\n".join(self.instance.caracteristicas or [])

    def clean_caracteristicas(self):
        return [
            linea.strip()
            for linea in self.cleaned_data["caracteristicas"].splitlines()
            if linea.strip()
        ]

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio

    def clean_stock(self):
        stock = self.cleaned_data["stock"]
        if stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")
        return stock

    def save(self, commit=True):
        caracteristicas = self.cleaned_data["caracteristicas"]
        if not caracteristicas and not self.instance.pk:
            caracteristicas = [f"Categoría: {self.cleaned_data['categoria']}"]
        self.instance.caracteristicas = caracteristicas
        return super().save(commit=commit)


class ConsultaClienteForm(forms.ModelForm):
    class Meta:
        model = ConsultaCliente
        fields = ["mensaje", "producto_interes"]
        widgets = {
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "producto_interes": forms.Select(attrs={"class": "form-control"}),
        }


class MensajeConsultaForm(forms.ModelForm):
    class Meta:
        model = MensajeConsulta
        fields = ["contenido"]
        widgets = {
            "contenido": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Escribe tu mensaje...",
            }),
        }