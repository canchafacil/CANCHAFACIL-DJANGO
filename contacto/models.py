from django.db import models


class Resena(models.Model):
    JUGADOR_CHOICES = [
        ('Amateur', 'Amateur'),
        ('Semi-profesional', 'Semi-profesional'),
        ('Profesional', 'Profesional'),
    ]
    CANCHA_CHOICES = [
        ('Fútbol 5', 'Fútbol 5'),
        ('Fútbol 7', 'Fútbol 7'),
        ('Fútbol 11', 'Fútbol 11'),
    ]

    nombre    = models.CharField(max_length=100)
    jugador   = models.CharField(max_length=50, choices=JUGADOR_CHOICES)
    cancha    = models.CharField(max_length=50, choices=CANCHA_CHOICES)
    estrellas = models.IntegerField(default=0)
    texto     = models.TextField()
    archivada = models.BooleanField(default=False)
    fecha     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nombre} - {self.cancha} ({self.estrellas}★)'