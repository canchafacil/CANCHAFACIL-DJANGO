from django.db import models
from reservas.models import Reserva


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
    correo    = models.EmailField(blank=True, null=True)
    jugador   = models.CharField(max_length=50, choices=JUGADOR_CHOICES)
    cancha    = models.CharField(max_length=50, choices=CANCHA_CHOICES)
    estrellas = models.IntegerField(default=0)
    texto     = models.TextField()
    archivada = models.BooleanField(default=False)
    fecha     = models.DateTimeField(auto_now_add=True)

    # Nuevo: vínculo directo a la reserva que originó la reseña.
    # null=True porque puede haber reseñas legacy sin reserva asociada.
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resena',
    )

    def __str__(self):
        return f'{self.nombre} - {self.cancha} ({self.estrellas}★)'