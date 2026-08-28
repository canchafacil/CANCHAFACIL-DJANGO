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

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resena',
    )

    def __str__(self):
        return f'{self.nombre} - {self.cancha} ({self.estrellas}★)'


class MensajeContacto(models.Model):
    """
    Mensajes enviados desde el formulario público de Contáctanos.
    Solo lectura desde el panel admin, salvo el campo 'respondido'.
    """
    nombre    = models.CharField(max_length=100)
    apellido  = models.CharField(max_length=100, blank=True)
    correo    = models.EmailField()
    telefono  = models.CharField(max_length=20, blank=True)
    asunto    = models.CharField(max_length=100)
    mensaje   = models.TextField()
    fecha     = models.DateTimeField(auto_now_add=True)
    respondido = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.nombre} {self.apellido} - {self.asunto}'