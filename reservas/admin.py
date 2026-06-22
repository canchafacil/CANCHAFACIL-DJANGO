from django.contrib import admin
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'telefono', 'cancha', 'fecha', 'hora', 'duracion')
    list_filter = ('cancha', 'fecha')
    search_fields = ('nombre', 'correo', 'telefono')
    ordering = ('-fecha',)