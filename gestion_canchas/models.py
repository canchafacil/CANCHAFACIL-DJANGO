from django.db import models

class Cancha(models.Model):
    TIPOS = [
        ('Fútbol 5', 'Fútbol 5'),
        ('Fútbol 7', 'Fútbol 7'),
        ('Fútbol 11', 'Fútbol 11'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='Fútbol 5')
    descripcion = models.TextField(blank=True)
    # Pesos colombianos: no se manejan centavos, por eso es un entero positivo
    # en vez de DecimalField. Ej: 120000 se muestra como "$120.000".
    precio = models.PositiveIntegerField(help_text="Valor por hora en pesos colombianos (COP), sin decimales")
    imagen = models.ImageField(upload_to='canchas/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Cancha'
        verbose_name_plural = 'Canchas'
        ordering = ['-creada']