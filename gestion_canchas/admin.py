from django.contrib import admin
from .models import Cancha

@admin.register(Cancha)
class CanchaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'precio', 'disponible', 'creada')
    list_filter = ('tipo', 'disponible')
    search_fields = ('nombre', 'descripcion')
    ordering = ('-creada',)
    readonly_fields = ('creada',)