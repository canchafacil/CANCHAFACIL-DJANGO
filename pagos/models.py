from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta


class Reserva(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_CONFIRMADA = 'confirmada'
    ESTADO_COMPLETADA = 'completada'
    ESTADO_CANCELADA = 'cancelada'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_COMPLETADA, 'Completada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    nombre   = models.CharField(max_length=100)
    correo   = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    fecha    = models.DateField()
    hora     = models.TimeField()  # primera hora de la reserva (compatibilidad / orden)

    # NUEVO: todas las horas reservadas, ej: ["18:00", "19:00", "20:00"]
    # Se guarda como JSON porque MariaDB no tiene ArrayField (eso es de Postgres).
    horas = models.JSONField(default=list, blank=True)

    cancha   = models.CharField(max_length=100)
    duracion = models.CharField(max_length=20)  # ej. "60 min", "2 horas", "3 Horas"
    estado   = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    numero_factura = models.CharField(max_length=20, blank=True, null=True)

    # ── ABONO / PAGO PARCIAL ──────────────────────────────────────
    TIPO_PAGO_COMPLETO = 'completo'
    TIPO_PAGO_ABONO = 'abono'
    TIPO_PAGO_CHOICES = [
        (TIPO_PAGO_COMPLETO, 'Pago completo'),
        (TIPO_PAGO_ABONO, 'Abono (50%)'),
    ]
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO_CHOICES, blank=True, null=True)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # ── PASARELA DE PAGO REAL (Mercado Pago / Stripe) ──────────────
    PASARELA_SIMULADO = 'simulado'
    PASARELA_MERCADOPAGO = 'mercadopago'
    PASARELA_STRIPE = 'stripe'
    PASARELA_CHOICES = [
        (PASARELA_SIMULADO, 'Simulado'),
        (PASARELA_MERCADOPAGO, 'Mercado Pago'),
        (PASARELA_STRIPE, 'Stripe'),
    ]
    pasarela = models.CharField(max_length=20, choices=PASARELA_CHOICES, blank=True, null=True)

    # ID que devuelve la pasarela al crear la preferencia/sesión (antes de pagar)
    referencia_pago = models.CharField(max_length=120, blank=True, null=True)

    # ID del pago/cargo YA confirmado por la pasarela (payment_id de MP, payment_intent de Stripe)
    referencia_pago_confirmado = models.CharField(max_length=120, blank=True, null=True)

    # True solo cuando el webhook confirma que el dinero realmente llegó
    pago_verificado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} - {self.cancha} - {self.fecha}"

    def duracion_minutos(self):
        """Convierte 'duracion' (ej. '60 min', '2 horas') a minutos enteros."""
        texto = self.duracion.lower().strip()
        if 'min' in texto:
            return int(texto.replace('min', '').strip())
        elif 'hora' in texto:
            horas = float(texto.replace('horas', '').replace('hora', '').strip())
            return int(horas * 60)
        else:
            try:
                return int(texto)
            except Exception:
                return 60

def precio_por_hora(self):
    """
    Consulta el precio real desde el modelo Cancha (gestion_canchas),
    que es la MISMA fuente que usa el formulario de reservas para
    armar CANCHAS_DATA.
    """
    from gestion_canchas.models import Cancha
    cancha_obj = Cancha.objects.filter(nombre=self.cancha).first()
    if cancha_obj:
        return cancha_obj.precio
    return 0
    def calcular_total(self):
        """
        Si hay 'horas' explícitas, el total es precio_hora * cantidad_de_horas
        (más preciso que calcular con duracion_minutos, sobre todo si algún
        día las horas dejan de ser bloques de 60 min exactos).
        """
        precio_hora = Decimal(self.precio_por_hora())
        if self.horas:
            return precio_hora * Decimal(len(self.horas))
        minutos = self.duracion_minutos()
        horas = Decimal(minutos) / 60
        return precio_hora * horas

    def calcular_abono_50(self):
        """Valor del 50% del total, redondeado a peso entero."""
        return (self.calcular_total() / 2).quantize(Decimal('1'))

    @property
    def esta_totalmente_pagada(self):
        return self.saldo_pendiente <= 0 and self.estado in (self.ESTADO_CONFIRMADA, self.ESTADO_COMPLETADA)

    def get_horas(self):
        """
        Devuelve siempre una lista de horas 'HH:MM', incluso para reservas
        viejas creadas antes de que existiera el campo 'horas'.
        """
        if self.horas:
            return self.horas
        return [self.hora.strftime('%H:%M')]

    # ------------------------------------------------------------------
    # Lógica de estados
    # ------------------------------------------------------------------
    def fecha_hora_fin(self):
        """Devuelve el datetime en que termina la reserva (fecha + última hora + 1h)."""
        horas_lista = self.get_horas()
        ultima_hora_str = sorted(horas_lista)[-1]
        h, m = map(int, ultima_hora_str.split(':'))
        inicio_ultima = datetime.combine(self.fecha, datetime.min.time().replace(hour=h, minute=m))
        inicio_ultima = timezone.make_aware(inicio_ultima) if timezone.is_naive(inicio_ultima) else inicio_ultima
        return inicio_ultima + timedelta(hours=1)

    def ya_paso(self):
        """True si la fecha/hora de la reserva (última hora reservada) ya pasó."""
        return timezone.now() >= self.fecha_hora_fin()

    def sincronizar_estado(self):
        """
        Si la reserva está confirmada y ya pasó su fecha/hora, la marca
        automáticamente como completada. No toca canceladas ni pendientes.
        Devuelve True si hubo cambio (para poder hacer bulk_update si se desea).
        """
        if self.estado == self.ESTADO_CONFIRMADA and self.ya_paso():
            self.estado = self.ESTADO_COMPLETADA
            self.save(update_fields=['estado'])
            return True
        return False

    @property
    def puede_editarse(self):
        """
        Solo se puede editar si está pendiente o confirmada Y todavía no
        ha pasado la fecha/hora. Completadas y canceladas nunca se editan.
        """
        if self.estado not in (self.ESTADO_PENDIENTE, self.ESTADO_CONFIRMADA):
            return False
        return not self.ya_paso()

    # Nota: NO se sobreescribe delete() a propósito. El bloqueo de borrado
    # se hace a nivel de vistas (nunca se expone una URL/acción que llame
    # a .delete() sobre una Reserva), así el modelo queda flexible para
    # uso interno del admin de Django si alguna vez hace falta.