from django.db import models


class Sede(models.Model):
    nombre    = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    ciudad    = models.CharField(max_length=100)
    telefono  = models.CharField(max_length=15, blank=True)
    activa    = models.BooleanField(default=True)
    creada    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'
        ordering = ['nombre']


from django.db import models
from django.core.exceptions import ValidationError

class Cancha(models.Model):
    TIPOS = [
        ('Fútbol 5', 'Fútbol 5'),
        ('Fútbol 7', 'Fútbol 7'),
        ('Fútbol 11', 'Fútbol 11'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='Fútbol 5')
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='canchas/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    def clean(self):
        """Validación a nivel de modelo"""
        if self.precio < 50000:
            raise ValidationError({
                'precio': 'El precio mínimo por hora es de $50,000 COP.'
            })

    def save(self, *args, **kwargs):
        """Ejecutar validación antes de guardar"""
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Cancha'
        verbose_name_plural = 'Canchas'
        ordering = ['-creada']