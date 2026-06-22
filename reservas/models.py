from django.db import models

class Reserva(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    fecha = models.DateField()
    hora = models.CharField(max_length=10)
    cancha = models.CharField(max_length=100)
    duracion = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.nombre} - {self.fecha} {self.hora}"