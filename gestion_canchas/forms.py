from django import forms
from .models import Cancha

class CanchaForm(forms.ModelForm):
    class Meta:
        model = Cancha
        fields = '__all__'
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }