from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta


# Minutos que tiene el cliente para pagar antes de que la reserva pendiente se cancele
MINUTOS_PARA_PAGAR = 15


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

    MOTIVO_VENCIDA = 'vencida'

    MOTIVOS_CANCELACION = [
        ('clima',   'Mal clima / cancha en mal estado'),
        ('equipo',  'No se completó el equipo'),
        ('horario', 'Se me cruzó con otro compromiso'),
        ('error',   'Me equivoqué al reservar (fecha, hora o cancha)'),
        ('salud',   'Motivos de salud o lesión'),
        ('precio',  'Encontré otra opción / tema de precio'),
        ('otro',    'Otro motivo'),
        (MOTIVO_VENCIDA, 'No se realizó el pago en 15 minutos'),
    ]

    CANCELADA_POR_CHOICES = [
        ('usuario', 'Usuario'),
        ('admin', 'Administrador'),
        ('sistema', 'Sistema (pago no realizado a tiempo)'),
    ]

    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    fecha = models.DateField()
    hora = models.TimeField()
    horas = models.JSONField(default=list, blank=True)
    cancha = models.CharField(max_length=100)
    duracion = models.CharField(max_length=20)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    numero_factura = models.CharField(max_length=20, blank=True, null=True)

    # Momento en que se creó la reserva (para el límite de 15 min de pago).
    # null=True: las reservas anteriores a este cambio quedan sin fecha y NUNCA se cancelan solas.
    creada_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)

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

    # ── MERCADO PAGO ──────────────────────────────────────────────
    mp_preference_id = models.CharField(max_length=255, blank=True, null=True)

    # ── CANCELACIÓN ────────────────────────────────────────────────
    motivo_cancelacion = models.CharField(
        max_length=20, choices=MOTIVOS_CANCELACION,
        blank=True, null=True, verbose_name="Motivo de cancelación"
    )
    motivo_detalle = models.TextField(blank=True, null=True, verbose_name="Detalle del motivo")
    fecha_cancelacion = models.DateTimeField(blank=True, null=True)
    cancelada_por = models.CharField(
        max_length=20, choices=CANCELADA_POR_CHOICES, blank=True, null=True
    )

    def __str__(self):
        return f"{self.nombre} - {self.cancha} - {self.fecha}"

    def duracion_minutos(self):
        """Convierte 'duracion' (ej. '60 min', '2 horas') a minutos enteros."""
        texto = (self.duracion or '').lower().strip()
        if not texto:
            return 60
        if 'min' in texto:
            try:
                return int(texto.replace('min', '').strip())
            except ValueError:
                return 60
        elif 'hora' in texto:
            try:
                horas = float(texto.replace('horas', '').replace('hora', '').strip())
                return int(horas * 60)
            except ValueError:
                return 60
        else:
            try:
                return int(texto)
            except Exception:
                return 60

    def precio_por_hora(self):
        """Obtiene el precio por hora desde Cancha; fallback 50000."""
        from gestion_canchas.models import Cancha
        try:
            cancha = Cancha.objects.get(nombre=self.cancha)
            return float(cancha.precio)
        except Cancha.DoesNotExist:
            return 50000.0

    def calcular_total(self):
        precio_hora = Decimal(self.precio_por_hora())
        if self.horas:
            return precio_hora * Decimal(len(self.horas))
        minutos = self.duracion_minutos()
        horas = Decimal(minutos) / 60
        return precio_hora * horas

    def calcular_abono_50(self):
        return (self.calcular_total() / 2).quantize(Decimal('1'))

    @property
    def esta_totalmente_pagada(self):
        return self.saldo_pendiente <= 0 and self.estado in (self.ESTADO_CONFIRMADA, self.ESTADO_COMPLETADA)

    def get_horas(self):
        """Devuelve lista de horas 'HH:MM'."""
        if self.horas:
            return self.horas
        if self.hora:
            return [self.hora.strftime('%H:%M')]
        return []

    @property
    def duracion_texto(self):
        """Duración legible calculada a partir de las horas reservadas."""
        n = len(self.get_horas())
        if n == 0:
            return "Sin duración"
        if n == 1:
            return "1 hora"
        return f"{n} horas"

    def fecha_hora_fin(self):
        horas_lista = self.get_horas()
        if not horas_lista:
            inicio = datetime.combine(self.fecha, datetime.min.time())
            inicio = timezone.make_aware(inicio) if timezone.is_naive(inicio) else inicio
            return inicio
        ultima_hora_str = sorted(horas_lista)[-1]
        h, m = map(int, ultima_hora_str.split(':'))
        inicio_ultima = datetime.combine(self.fecha, datetime.min.time().replace(hour=h, minute=m))
        inicio_ultima = timezone.make_aware(inicio_ultima) if timezone.is_naive(inicio_ultima) else inicio_ultima
        return inicio_ultima + timedelta(hours=1)

    def ya_paso(self):
        return timezone.now() >= self.fecha_hora_fin()

    def sincronizar_estado(self):
        if self.estado == self.ESTADO_CONFIRMADA and self.ya_paso():
            self.estado = self.ESTADO_COMPLETADA
            self.save(update_fields=['estado'])
            return True
        return False

    # ── LÍMITE DE PAGO (15 min) ───────────────────────────────────
    @property
    def expira_en(self):
        """Momento en que vence el pago. None si la reserva no corre contra reloj."""
        if (
            self.estado != self.ESTADO_PENDIENTE
            or not self.creada_en
            or (self.monto_pagado or Decimal('0')) > 0
        ):
            return None
        return self.creada_en + timedelta(minutes=MINUTOS_PARA_PAGAR)

    @property
    def segundos_para_pagar(self):
        """Segundos que le quedan al cliente para pagar (None si no aplica)."""
        limite = self.expira_en
        if not limite:
            return None
        return max(0, int((limite - timezone.now()).total_seconds()))

    @property
    def puede_editarse(self):
        if self.estado not in (self.ESTADO_PENDIENTE, self.ESTADO_CONFIRMADA):
            return False
        return not self.ya_paso()

    @property
    def motivo_legible(self):
        if not self.motivo_cancelacion:
            return "Sin motivo registrado"
        return dict(self.MOTIVOS_CANCELACION).get(self.motivo_cancelacion, self.motivo_cancelacion)

    def cancelar(self, motivo, detalle='', por='usuario'):
        self.estado = self.ESTADO_CANCELADA
        self.motivo_cancelacion = motivo
        self.motivo_detalle = detalle or None
        self.fecha_cancelacion = timezone.now()
        self.cancelada_por = por
        self.save(update_fields=[
            'estado', 'motivo_cancelacion', 'motivo_detalle',
            'fecha_cancelacion', 'cancelada_por'
        ])