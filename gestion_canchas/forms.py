from django import forms
from django.core.exceptions import ValidationError
from .models import Cancha


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


class CanchaForm(forms.ModelForm):
    class Meta:
        model = Cancha
        fields = '__all__'
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'min': 50000, 'step': 1000}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_precio(self):
        """Validación específica para el campo precio"""
        precio = self.cleaned_data.get('precio')
        if precio is None or precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        if precio < 50000:
            raise forms.ValidationError('El precio mínimo por hora es de $50,000 COP.')
        return precio