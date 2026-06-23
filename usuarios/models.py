from django.db import models

class Usuario(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=100)
    rol = models.CharField(max_length=20, default='USER')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"