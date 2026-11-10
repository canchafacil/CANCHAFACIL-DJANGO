import logging
from decimal import Decimal

import mercadopago
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from reservas.models import Reserva
from .utils import generar_factura_pdf

logger = logging.getLogger(__name__)


def monto_esperado(reserva):
    """Monto que el servidor espera cobrar, según el tipo de pago."""
    if reserva.tipo_pago == Reserva.TIPO_PAGO_ABONO:
        return reserva.calcular_abono_50()
    return reserva.calcular_total().quantize(Decimal('1'))


def consultar_pago(payment_id):
    """Consulta el pago directamente a Mercado Pago."""
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    resp = sdk.payment().get(payment_id)
    if resp.get('status') != 200:
        logger.warning("MP no devolvió el pago %s: %s", payment_id, resp)
        return None
    return resp.get('response')


def enviar_correo_confirmacion_pago(reserva):
    """Envía el correo de confirmación con la factura en PDF adjunta."""
    try:
        html = render_to_string('pagos/confirmacion_pago.html', {'reserva': reserva})
        msg = EmailMultiAlternatives(
            subject=f"Confirmación de tu reserva - {reserva.numero_factura}",
            body=strip_tags(html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reserva.correo],
        )
        msg.attach_alternative(html, "text/html")
        pdf = generar_factura_pdf(reserva.id)
        if pdf:
            msg.attach(f"factura_{reserva.id}.pdf", pdf.getvalue(), "application/pdf")
        msg.send()
    except Exception:
        logger.exception("No se pudo enviar el correo de la reserva %s", reserva.id)


def registrar_pago_aprobado(payment):
    """
    Registra un pago aprobado de Mercado Pago. Es idempotente: se puede llamar
    desde el retorno del navegador y desde el webhook sin duplicar nada.
    Devuelve la reserva (o None si el pago no es válido).
    """
    if not payment or payment.get('status') != 'approved':
        return None

    try:
        reserva_id = int(payment.get('external_reference'))
    except (TypeError, ValueError):
        return None

    payment_id = str(payment['id'])

    with transaction.atomic():
        try:
            reserva = Reserva.objects.select_for_update().get(id=reserva_id)
        except Reserva.DoesNotExist:
            return None

        # Ya procesado (por el retorno o por el webhook)
        if reserva.mp_payment_id == payment_id or reserva.estado == Reserva.ESTADO_CONFIRMADA:
            return reserva

        if reserva.estado == Reserva.ESTADO_CANCELADA:
            logger.warning("Pago %s aprobado para reserva cancelada %s", payment_id, reserva.id)
            return None

        # Validar el monto contra lo que el servidor esperaba cobrar
        pagado = Decimal(str(payment.get('transaction_amount', 0)))
        if abs(pagado - monto_esperado(reserva)) > 1:
            logger.error("Monto inesperado en pago %s: %s vs %s",
                         payment_id, pagado, monto_esperado(reserva))
            return None

        total = reserva.calcular_total().quantize(Decimal('1'))
        reserva.mp_payment_id = payment_id
        reserva.estado = Reserva.ESTADO_CONFIRMADA
        reserva.metodo_pago = 'Mercado Pago'
        reserva.precio_total = total
        reserva.monto_pagado = pagado
        reserva.saldo_pendiente = max(total - pagado, Decimal('0'))
        reserva.numero_factura = f"FAC-{reserva.id:06d}"
        reserva.save()

        # El correo sale solo cuando la transacción ya se confirmó
        transaction.on_commit(lambda: enviar_correo_confirmacion_pago(reserva))

    return reserva