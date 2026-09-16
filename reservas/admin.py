from django.contrib import admin
from django.utils.html import format_html
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'telefono', 'cancha', 'fecha', 'hora', 'duracion', 'estado_coloreado', 'motivo_admin')
    list_filter = ('estado', 'motivo_cancelacion', 'cancha', 'fecha')
    search_fields = ('nombre', 'correo', 'telefono', 'motivo_detalle')
    ordering = ('-fecha',)
    readonly_fields = ('fecha_cancelacion', 'cancelada_por')

    fieldsets = (
        ('Datos de la reserva', {
            'fields': ('nombre', 'correo', 'telefono', 'cancha', 'fecha', 'hora', 'horas',
                       'duracion', 'estado', 'metodo_pago', 'precio_total', 'numero_factura')
        }),
        ('Pago', {
            'classes': ('collapse',),
            'fields': ('tipo_pago', 'monto_pagado', 'saldo_pendiente', 'mp_preference_id')
        }),
        ('Cancelación', {
            'classes': ('collapse',),
            'fields': ('motivo_cancelacion', 'motivo_detalle', 'fecha_cancelacion', 'cancelada_por')
        }),
    )

    @admin.display(description='Estado')
    def estado_coloreado(self, obj):
        colores = {
            'pendiente': '#ffc107',
            'confirmada': '#0dcaf0',
            'completada': '#198754',
            'cancelada': '#6c757d',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;">{}</span>',
            colores.get(obj.estado, '#adb5bd'), obj.get_estado_display()
        )

    @admin.display(description='Motivo de cancelación')
    def motivo_admin(self, obj):
        if obj.estado != Reserva.ESTADO_CANCELADA:
            return '—'
        detalle = f'<br><small style="color:#666;">{obj.motivo_detalle}</small>' if obj.motivo_detalle else ''
        return format_html('<strong style="color:#b02a37;">{}</strong>{}', obj.motivo_legible, detalle)