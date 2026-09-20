from django.db import models
from usuarios.models import Usuario
from gestion_canchas.models import Cancha
from reservas.models import Reserva


class PartidoAbierto(models.Model):
    reserva = models.OneToOneField(
        Reserva, on_delete=models.CASCADE, related_name='partido_abierto'
    )
    cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE, related_name='partidos_abiertos')
    fecha = models.DateField()                 # fecha real del partido (copiada de la reserva)
    hora_texto = models.CharField(max_length=100)  # Ej: "7:00 PM – 8:00 PM"
    jugadores_faltan = models.PositiveIntegerField(default=1)
    creador = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='partidos_creados')
    participantes = models.ManyToManyField(Usuario, related_name='partidos_unidos', blank=True)
    cobra = models.BooleanField(default=False)
    valor = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', '-creado']

    def __str__(self):
        return f"{self.cancha} - {self.fecha} {self.hora_texto}"


class Reto(models.Model):
    reserva = models.OneToOneField(
        Reserva, on_delete=models.CASCADE, related_name='reto'
    )
    equipo = models.CharField(max_length=100)
    cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE, related_name='retos')
    horario = models.CharField(max_length=100)
    creador = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='retos_creados')
    aceptado = models.BooleanField(default=False)
    aceptado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='retos_aceptados'
    )
    cobra = models.BooleanField(default=False)
    valor = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"{self.equipo} - {self.cancha}"


class Aporte(models.Model):
    """Pago que hace un jugador al unirse a un partido o aceptar un reto que cobra."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='aportes')
    partido = models.ForeignKey(
        PartidoAbierto, on_delete=models.CASCADE, related_name='aportes', null=True, blank=True
    )
    reto = models.ForeignKey(
        Reto, on_delete=models.CASCADE, related_name='aportes', null=True, blank=True
    )
    monto = models.PositiveIntegerField()
    pagado = models.BooleanField(default=False)
    mp_preference_id = models.CharField(max_length=255, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        destino = self.partido or self.reto
        return f"{self.usuario} - {self.monto} ({destino})"


class PublicacionMuro(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='publicaciones_muro')
    nombre_mostrar = models.CharField(max_length=100)
    texto = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"{self.nombre_mostrar}: {self.texto[:30]}"