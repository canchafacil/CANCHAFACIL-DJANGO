from datetime import timedelta

from django.utils import timezone

from .models import Reserva, MINUTOS_PARA_PAGAR


def cancelar_reservas_vencidas():
    """
    Cancela las reservas PENDIENTES que llevan más de 15 minutos sin ningún pago
    y libera sus horas. Devuelve cuántas canceló.

    - Solo toca reservas con creada_en (las viejas, sin fecha, nunca se cancelan solas).
    - Nunca toca reservas con algún pago registrado ni las confirmadas.
    - El UPDATE vuelve a validar las condiciones, así dos procesos al tiempo
      no cancelan (ni envían correo) dos veces, y un pago que acaba de entrar gana.
    """
    limite = timezone.now() - timedelta(minutes=MINUTOS_PARA_PAGAR)

    condiciones = dict(
        estado=Reserva.ESTADO_PENDIENTE,
        creada_en__isnull=False,
        creada_en__lt=limite,
        monto_pagado__lte=0,
    )

    ids = list(Reserva.objects.filter(**condiciones).values_list('id', flat=True))
    canceladas = []

    for pk in ids:
        actualizadas = Reserva.objects.filter(pk=pk, **condiciones).update(
            estado=Reserva.ESTADO_CANCELADA,
            motivo_cancelacion=Reserva.MOTIVO_VENCIDA,
            motivo_detalle=None,
            fecha_cancelacion=timezone.now(),
            cancelada_por='sistema',
        )
        if actualizadas:
            canceladas.append(pk)

    if canceladas:
        # import aquí para evitar import circular (views importa utils)
        from .views import _enviar_correo_cancelacion
        for reserva in Reserva.objects.filter(pk__in=canceladas):
            _enviar_correo_cancelacion(reserva, copia_admin=False)

    return len(canceladas)