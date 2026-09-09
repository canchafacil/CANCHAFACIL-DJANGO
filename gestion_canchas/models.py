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


class Cancha(models.Model):
    TIPOS = [
        ('Fútbol 5',  'Fútbol 5'),
        ('Fútbol 7',  'Fútbol 7'),
        ('Fútbol 11', 'Fútbol 11'),
    ]

    # ← única línea nueva: FK a Sede
    # null=True/blank=True para que las canchas existentes no rompan
    sede = models.ForeignKey(
        Sede,
        on_delete=models.SET_NULL,
        related_name='canchas',
        null=True,
        blank=True,
        verbose_name='Sede'
    )

    nombre     = models.CharField(max_length=100)
    tipo       = models.CharField(max_length=20, choices=TIPOS, default='Fútbol 5')
    descripcion = models.TextField(blank=True)
    precio     = models.PositiveIntegerField(
                    help_text="Valor por hora en pesos colombianos (COP), sin decimales"
                  )
    imagen     = models.ImageField(upload_to='canchas/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    creada     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.sede:
            return f"{self.nombre} — {self.sede.nombre}"
        return self.nombre

    class Meta:
        verbose_name = 'Cancha'
        verbose_name_plural = 'Canchas'
        ordering = ['-creada']