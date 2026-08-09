from django import forms
from .models import Cancha

class CanchaForm(forms.ModelForm):
    class Meta:
        model = Cancha
        fields = '__all__'
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Breve descripción de la cancha (ubicación, características, superficie, etc.)'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            # step=1000 para que el spinner del navegador suba/baje de mil en mil pesos
            'precio': forms.NumberInput(attrs={'step': '1000', 'min': '0', 'class': 'form-control', 'placeholder': 'Ej: 120000'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }