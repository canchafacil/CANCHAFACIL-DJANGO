from django import forms
from django.core.exceptions import ValidationError
from .models import Cancha, Sede


class CanchaForm(forms.ModelForm):
    class Meta:
        model = Cancha
        fields = '__all__'
        widgets = {
            'sede': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Cancha Principal'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 
                                                 'placeholder': 'Ubicación, superficie, características...'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'min': 50000, 'step': 1000,
                                               'placeholder': 'Ej: 120000'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None or precio < 50000:
            raise ValidationError('El precio mínimo por hora es de $50,000 COP.')
        return precio