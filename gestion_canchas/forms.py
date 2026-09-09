from django import forms
from .models import Cancha, Sede


class CanchaForm(forms.ModelForm):
    class Meta:
        model  = Cancha
        fields = '__all__'
        widgets = {
            # ← nuevo
            'sede': forms.Select(attrs={
                'class': 'form-select form-control'
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Breve descripción de la cancha (ubicación, características, superficie, etc.)'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'precio': forms.NumberInput(attrs={
                'step': '1000',
                'min': '0',
                'class': 'form-control',
                'placeholder': 'Ej: 120000'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'disponible': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo muestra sedes activas en el selector
        self.fields['sede'].empty_label = 'Sin sede asignada'
        self.fields['sede'].queryset    = Sede.objects.filter(activa=True).order_by('nombre')


# ── Nuevo ─────────────────────────────────────────────
class SedeForm(forms.ModelForm):
    class Meta:
        model  = Sede
        fields = ['nombre', 'direccion', 'ciudad', 'telefono', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Sede Norte'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección completa'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 3001234567'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }