from django.db import models


class Usuario(models.Model):

    ROLES = [
        ('SUPERADMIN', 'Super Administrador'),
        ('ADMIN', 'Administrador'),
        ('CLIENTE', 'Cliente'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10)
    password = models.CharField(max_length=100)

    rol = models.CharField(
        max_length=15,
        choices=ROLES
    )

    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} ({self.rol})"


class AuditoriaRol(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='auditorias_rol')
    rol_anterior = models.CharField(max_length=15, null=True, blank=True)
    rol_nuevo = models.CharField(max_length=15)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario} : {self.rol_anterior} → {self.rol_nuevo} ({self.fecha})"