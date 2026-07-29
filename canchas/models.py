from django.db import models


class Cancha(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, default='Fútbol 5')
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='canchas/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class AuditoriaCancha(models.Model):
    cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE, related_name='auditorias')
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_nuevo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    disponible_anterior = models.BooleanField(null=True, blank=True)
    disponible_nuevo = models.BooleanField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cancha} actualizada el {self.fecha}"