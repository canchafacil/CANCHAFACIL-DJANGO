import json
import mercadopago
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from .models import Reserva
from usuarios.models import Usuario
from gestion_canchas.models import Cancha


# =================================================================
# CONSTANTES Y AUXILIARES
# =================================================================

HORAS_VALIDAS = [
    '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
    '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
    '18:00', '19:00', '20:00', '21:00', '22:00'
]


def _horas_son_consecutivas(horas):
    if not horas:
        return False
    if len(set(horas)) != len(horas):
        return False
    try:
        indices = sorted(HORAS_VALIDAS.index(h) for h in horas)
    except ValueError:
        return False
    for i in range(1, len(indices)):
        if indices[i] != indices[i - 1] + 1:
            return False
    return True


def _sincronizar_todas(queryset):
    for r in queryset:
        r.sincronizar_estado()


def _horas_ocupadas(cancha, fecha, excluir_id=None):
    qs = Reserva.objects.filter(cancha=cancha, fecha=fecha).exclude(estado=Reserva.ESTADO_CANCELADA)
    if excluir_id is not None:
        qs = qs.exclude(id=excluir_id)
    ocupadas = set()
    for r in qs:
        ocupadas.update(r.get_horas())
    return ocupadas


def _duracion_desde_horas(horas):
    n = len(horas)
    if n == 1:
        return "60 min"
    return f"{n} horas"


def _to_decimal(valor, default='0'):
    if valor is None:
        return Decimal(default)
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


# =================================================================
# VISTAS PRINCIPALES
# =================================================================

def pagina_reservas(request):
    return render(request, "reservas/reservas.html")


def reservas(request, cancha_id=None):
    todas = Reserva.objects.exclude(estado=Reserva.ESTADO_CANCELADA).order_by('-id')
    _sincronizar_todas(todas)

    canchas = Cancha.objects.filter(disponible=True)

    usuario = None
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        usuario = Usuario.objects.filter(id=usuario_id).first()

    return render(request, "reservas/formulario.html", {
        "reservas": todas,
        "canchas": canchas,
        "usuario": usuario,
        "cancha_id": cancha_id,
        "tiene_reserva_activa": False,
    })


@require_POST
def crear_reserva(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return JsonResponse({"status": "error", "mensaje": "Debes iniciar sesión", "redirect": "login"}, status=401)

    try:
        usuario = Usuario.objects.get(id=usuario_id)

        data = json.loads(request.body.decode("utf-8"))

        horas_solicitadas = data.get("horas") or [data["hora"]]
        if not isinstance(horas_solicitadas, list) or len(horas_solicitadas) == 0:
            return JsonResponse({"status": "error", "mensaje": "Debes seleccionar al menos una hora."}, status=400)

        if not _horas_son_consecutivas(horas_solicitadas):
            return JsonResponse(
                {"status": "error", "mensaje": "Las horas seleccionadas deben ser continuas, sin saltos."},
                status=400
            )

        ocupadas = _horas_ocupadas(data["cancha"], data["fecha"])
        if any(h in ocupadas for h in horas_solicitadas):
            return JsonResponse(
                {"status": "error", "mensaje": "Una o más horas seleccionadas ya están ocupadas."},
                status=409
            )

        horas_ordenadas = sorted(horas_solicitadas)

        reserva = Reserva.objects.create(
            nombre   = f"{usuario.first_name} {usuario.last_name}".strip(),
            correo   = usuario.email,
            telefono = usuario.phone,
            fecha    = data["fecha"],
            hora     = horas_ordenadas[0],
            horas    = horas_ordenadas,
            cancha   = data["cancha"],
            duracion = _duracion_desde_horas(horas_ordenadas),
        )
        request.session["reserva_pendiente_id"] = reserva.id
        return JsonResponse({"status": "ok", "id": reserva.id})
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "mensaje": "Datos inválidos"}, status=400)


@require_POST
def editar_reserva(request, id):
    try:
        reserva = Reserva.objects.get(id=id)
        reserva.sincronizar_estado()

        if not reserva.puede_editarse:
            return JsonResponse(
                {"status": "error", "mensaje": "Esta reserva ya no se puede editar."},
                status=403
            )

        data = json.loads(request.body.decode("utf-8"))

        nueva_fecha  = data.get("fecha", str(reserva.fecha))
        nueva_cancha = data.get("cancha", reserva.cancha)
        horas_nuevas = data.get("horas") or [data.get("hora", reserva.hora.strftime('%H:%M'))]

        if not isinstance(horas_nuevas, list) or len(horas_nuevas) == 0:
            return JsonResponse({"status": "error", "mensaje": "Debes seleccionar al menos una hora."}, status=400)

        if not _horas_son_consecutivas(horas_nuevas):
            return JsonResponse(
                {"status": "error", "mensaje": "Las horas seleccionadas deben ser continuas, sin saltos."},
                status=400
            )

        ocupadas = _horas_ocupadas(nueva_cancha, nueva_fecha, excluir_id=reserva.id)
        if any(h in ocupadas for h in horas_nuevas):
            return JsonResponse(
                {"status": "error", "mensaje": "Una o más horas seleccionadas ya están ocupadas."},
                status=409
            )

        horas_ordenadas = sorted(horas_nuevas)

        reserva.nombre   = data.get("nombre",   reserva.nombre)
        reserva.correo   = data.get("correo",   reserva.correo)
        reserva.telefono = data.get("telefono", reserva.telefono)
        reserva.fecha    = nueva_fecha
        reserva.hora     = horas_ordenadas[0]
        reserva.horas    = horas_ordenadas
        reserva.cancha   = nueva_cancha
        reserva.duracion = _duracion_desde_horas(horas_ordenadas)

        nuevo_total    = reserva.calcular_total()
        monto_ya_pagado = reserva.monto_pagado or Decimal('0')
        reserva.precio_total    = nuevo_total
        reserva.saldo_pendiente = max(Decimal('0'), nuevo_total - monto_ya_pagado)

        reserva.save()
        return JsonResponse({
            "status": "ok",
            "nuevo_total": str(reserva.precio_total),
            "saldo_pendiente": str(reserva.saldo_pendiente),
        })
    except Reserva.DoesNotExist:
        return JsonResponse({"status": "error", "mensaje": "Reserva no encontrada"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)


# =================================================================
# EDICIÓN DESDE PERFIL (con cobro de diferencia y salvaguarda)
# =================================================================

@require_POST
def editar_reserva_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('usuarios:login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=id)

    if reserva.correo != usuario.email:
        return redirect('usuarios:perfil')

    reserva.sincronizar_estado()

    if not reserva.puede_editarse:
        messages.error(request, 'Esta reserva ya no se puede editar (pasó, o está cancelada/completada).')
        return redirect('usuarios:perfil')

    # 🔥 SALVAGUARDA: Reservas viejas que estaban confirmadas pero sin monto_pagado
    if reserva.estado == Reserva.ESTADO_CONFIRMADA and (reserva.monto_pagado or Decimal('0')) == 0:
        reserva.monto_pagado = reserva.precio_total or reserva.calcular_total()
        reserva.saldo_pendiente = Decimal('0')
        reserva.save(update_fields=['monto_pagado', 'saldo_pendiente'])

    nueva_fecha  = request.POST.get('fecha') or str(reserva.fecha)
    nueva_cancha = request.POST.get('cancha') or reserva.cancha

    horas_nuevas = request.POST.getlist('horas')
    if not horas_nuevas:
        messages.error(request, 'Debes seleccionar al menos una hora.')
        return redirect('usuarios:perfil')

    if not _horas_son_consecutivas(horas_nuevas):
        messages.error(request, 'Las horas deben ser continuas, sin saltos.')
        return redirect('usuarios:perfil')

    ocupadas = _horas_ocupadas(nueva_cancha, nueva_fecha, excluir_id=reserva.id)
    if any(h in ocupadas for h in horas_nuevas):
        messages.error(request, 'Una o más horas seleccionadas ya están ocupadas.')
        return redirect('usuarios:perfil')

    horas_ordenadas = sorted(horas_nuevas)

    # Aplicar cambios
    reserva.fecha    = nueva_fecha
    reserva.hora     = horas_ordenadas[0]
    reserva.horas    = horas_ordenadas
    reserva.cancha   = nueva_cancha
    reserva.duracion = _duracion_desde_horas(horas_ordenadas)

    # Recalcular montos
    nuevo_total     = reserva.calcular_total()
    monto_ya_pagado = reserva.monto_pagado or Decimal('0')

    reserva.precio_total    = nuevo_total
    reserva.saldo_pendiente = max(Decimal('0'), nuevo_total - monto_ya_pagado)

    try:
        reserva.full_clean()
        reserva.save()

        # Caso 1: ya pagó algo y ahora debe MÁS → cobrar diferencia
        if monto_ya_pagado > 0 and reserva.saldo_pendiente > 0:
            request.session['reserva_pendiente_id'] = reserva.id
            messages.warning(
                request,
                f'Agregaste horas a tu reserva. Nuevo total: ${nuevo_total:,.0f}. '
                f'Ya pagaste: ${monto_ya_pagado:,.0f}. '
                f'Debes pagar la diferencia de ${reserva.saldo_pendiente:,.0f}.'
            )
            return redirect('pago')

        # Caso 2: redujo horas y pagó de más → informar excedente
        if monto_ya_pagado > 0 and nuevo_total < monto_ya_pagado:
            excedente = monto_ya_pagado - nuevo_total
            messages.info(
                request,
                f'Redujiste tu reserva. Nueva tarifa: ${nuevo_total:,.0f}. '
                f'Ya habías pagado: ${monto_ya_pagado:,.0f}. '
                f'Excedente: ${excedente:,.0f}. Contacta al administrador para gestionar el reembolso.'
            )
            return redirect('usuarios:perfil')

        # Caso 3: pendiente sin pagos o pago exacto
        messages.success(request, 'Reserva actualizada correctamente.')

    except Exception as e:
        messages.error(request, f'No se pudo guardar: {e}')

    return redirect('usuarios:perfil')


@require_POST
def cancelar_reserva_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('usuarios:login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=id)

    if reserva.correo != usuario.email:
        return redirect('usuarios:perfil')

    reserva.sincronizar_estado()

    if reserva.estado not in (Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA):
        return redirect('usuarios:perfil')

    motivo = request.POST.get('motivo_cancelacion', '').strip()
    detalle = request.POST.get('motivo_detalle', '').strip()
    motivos_validos = dict(Reserva.MOTIVOS_CANCELACION)

    if motivo not in motivos_validos:
        return redirect('usuarios:perfil')

    if motivo == 'otro' and len(detalle) < 10:
        return redirect('usuarios:perfil')

    reserva.cancelar(motivo=motivo, detalle=detalle, por='usuario')
    _enviar_correo_cancelacion(reserva)

    return redirect('usuarios:perfil')


def _enviar_correo_cancelacion(reserva):
    contexto = {
        'reserva': reserva,
        'motivo': reserva.motivo_legible,
        'detalle': reserva.motivo_detalle,
    }
    cuerpo_html = render_to_string('emails/cancelacion_reserva.html', contexto)
    horas_texto = ", ".join(reserva.get_horas())
    cuerpo_texto = (
        f"Hola {reserva.nombre},\n\n"
        f"Tu reserva fue cancelada:\n"
        f"Cancha: {reserva.cancha}\n"
        f"Fecha: {reserva.fecha}\n"
        f"Hora(s): {horas_texto}\n"
        f"Motivo: {reserva.motivo_legible}\n"
        f"{('Detalle: ' + reserva.motivo_detalle) if reserva.motivo_detalle else ''}\n\n"
        f"Las horas quedaron disponibles nuevamente.\n\n"
        f"Equipo {settings.EMPRESA_NOMBRE}"
    )
    try:
        email = EmailMultiAlternatives(
            f"Reserva cancelada - {settings.EMPRESA_NOMBRE}",
            cuerpo_texto,
            settings.DEFAULT_FROM_EMAIL,
            [reserva.correo],
            bcc=[settings.DEFAULT_FROM_EMAIL],
        )
        email.attach_alternative(cuerpo_html, "text/html")
        email.send(fail_silently=False)
    except Exception as e:
        print(f"Error enviando correo de cancelación: {e}")


# =================================================================
# PAGO (con diferencia y cálculo del 50%)
# =================================================================

def pago(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    reserva = None
    total = 0
    ya_pagado = 0
    es_diferencia = False
    abono_50 = 0  # 🔥 Para que el HTML pinte el valor del 50% de una vez

    if reserva_id:
        try:
            reserva = Reserva.objects.get(id=reserva_id)

            monto_ya_pagado = reserva.monto_pagado or Decimal('0')
            saldo = reserva.saldo_pendiente or Decimal('0')

            if monto_ya_pagado > 0 and saldo > 0:
                # Diferencia
                total = float(saldo)
                ya_pagado = float(monto_ya_pagado)
                es_diferencia = True
                abono_50 = total
            elif monto_ya_pagado > 0 and saldo <= 0:
                # Ya está pagada
                total = 0
                ya_pagado = float(monto_ya_pagado)
            else:
                # Primera vez
                total = float(reserva.calcular_total())
                abono_50 = total / 2
        except Reserva.DoesNotExist:
            pass

    return render(request, "pagos/pago.html", {
        "reserva": reserva,
        "total": total,
        "ya_pagado": ya_pagado,
        "es_diferencia": es_diferencia,
        "abono_50": abono_50,
    })


@require_POST
def confirmar_pago(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    if not reserva_id:
        return JsonResponse({"status": "error", "mensaje": "No hay reserva pendiente"}, status=400)

    reserva = get_object_or_404(Reserva, id=reserva_id)
    data = json.loads(request.body.decode("utf-8")) if request.body else {}

    monto_ya_pagado = reserva.monto_pagado or Decimal('0')

    if monto_ya_pagado > 0 and (reserva.saldo_pendiente or Decimal('0')) > 0:
        # 🔥 Pago de DIFERENCIA
        monto_a_pagar = reserva.saldo_pendiente
        reserva.monto_pagado    = monto_ya_pagado + monto_a_pagar
        reserva.saldo_pendiente = Decimal('0')
        tipo_pago = Reserva.TIPO_PAGO_COMPLETO
    else:
        # Pago inicial normal
        tipo_pago = data.get("tipo_pago", Reserva.TIPO_PAGO_COMPLETO)
        if tipo_pago not in (Reserva.TIPO_PAGO_COMPLETO, Reserva.TIPO_PAGO_ABONO):
            return JsonResponse({"status": "error", "mensaje": "Tipo de pago inválido"}, status=400)

        total = reserva.calcular_total()
        monto_a_pagar = reserva.calcular_abono_50() if tipo_pago == Reserva.TIPO_PAGO_ABONO else total

        reserva.precio_total    = total
        reserva.monto_pagado    = monto_a_pagar
        reserva.saldo_pendiente = total - monto_a_pagar

    reserva.metodo_pago    = data.get("metodo_pago", "Simulado")
    reserva.tipo_pago      = tipo_pago
    reserva.numero_factura = reserva.numero_factura or f"FAC-{reserva.id:06d}"
    reserva.estado         = Reserva.ESTADO_CONFIRMADA
    reserva.save()

    enviar_correo_confirmacion(reserva)
    if "reserva_pendiente_id" in request.session:
        del request.session["reserva_pendiente_id"]

    return JsonResponse({
        "status": "ok",
        "mensaje": "Pago confirmado y correo enviado",
        "tipo_pago": tipo_pago,
        "monto_pagado": str(monto_a_pagar),
        "saldo_pendiente": str(reserva.saldo_pendiente),
    })


def enviar_correo_confirmacion(reserva):
    asunto = f"Confirmación de tu reserva - {settings.EMPRESA_NOMBRE}"
    contexto = {"reserva": reserva}

    cuerpo_html = render_to_string("reservas/confirmacion_reserva.html", contexto)
    horas_texto = ", ".join(reserva.get_horas())
    
    linea_pago = f"Pagaste el total: ${reserva.precio_total}"
    if reserva.tipo_pago == Reserva.TIPO_PAGO_ABONO and (reserva.saldo_pendiente or Decimal('0')) > 0:
        linea_pago = (
            f"Abonaste: ${reserva.monto_pagado} (50%)\n"
            f"Saldo pendiente a pagar en la cancha: ${reserva.saldo_pendiente}"
        )
    elif (reserva.saldo_pendiente or Decimal('0')) <= 0 and (reserva.monto_pagado or Decimal('0')) > 0:
        linea_pago = f"Pagaste el total: ${reserva.monto_pagado}"

    cuerpo_texto = (
        f"Hola {reserva.nombre},\n\n"
        f"Tu reserva ha sido confirmada:\n"
        f"Cancha: {reserva.cancha}\n"
        f"Fecha: {reserva.fecha}\n"
        f"Hora(s): {horas_texto}\n"
        f"Duración: {reserva.duracion_texto}\n"
        f"Valor total de la reserva: ${reserva.precio_total}\n"
        f"{linea_pago}\n"
        f"N° de factura: {reserva.numero_factura}\n\n"
        f"Equipo {settings.EMPRESA_NOMBRE}"
    )

    try:
        email = EmailMultiAlternatives(
            asunto,
            cuerpo_texto,
            settings.DEFAULT_FROM_EMAIL,
            [reserva.correo],
        )
        email.attach_alternative(cuerpo_html, "text/html")
        email.send(fail_silently=False)
    except Exception as e:
        print(f"Error enviando correo de confirmación: {e}")


# =================================================================
# MERCADO PAGO (con diferencia)
# =================================================================

@csrf_exempt
def crear_preferencia_mercadopago(request, reserva_id):
    if not request.session.get('usuario_id'):
        return redirect('usuarios:login')

    reserva = get_object_or_404(Reserva, id=reserva_id)
    usuario = get_object_or_404(Usuario, id=request.session['usuario_id'])

    if reserva.correo != usuario.email:
        return redirect('usuarios:perfil')

    monto_ya_pagado = reserva.monto_pagado or Decimal('0')
    saldo           = reserva.saldo_pendiente or Decimal('0')

    if reserva.estado == 'confirmada' and saldo <= 0:
        return redirect('pago_exitoso_mp')

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    if monto_ya_pagado > 0 and saldo > 0:
        total = int(saldo)
        es_diferencia = True
        tipo_pago = 'completo'
    else:
        monto_a_pagar = request.POST.get('monto_a_pagar')
        if monto_a_pagar:
            try:
                total = int(float(monto_a_pagar))
            except (ValueError, TypeError):
                total = int(float(reserva.calcular_total()))
        else:
            total = int(float(reserva.calcular_total()))
        es_diferencia = False
        tipo_pago = request.POST.get('tipo_pago', 'completo')

    dominio = request.build_absolute_uri('/').rstrip('/')
    es_local = ('127.0.0.1' in dominio) or ('localhost' in dominio)

    success_url = request.build_absolute_uri(reverse('pago_exitoso_mp'))
    failure_url = request.build_absolute_uri(reverse('pago_cancelado_mp'))
    pending_url = request.build_absolute_uri(reverse('pago_cancelado_mp'))

    if not es_local:
        success_url = success_url.replace('http://', 'https://')
        failure_url = failure_url.replace('http://', 'https://')
        pending_url = pending_url.replace('http://', 'https://')

    request.session['reserva_pendiente_id'] = reserva.id
    request.session['tipo_pago'] = tipo_pago
    request.session['monto_pagado'] = total
    request.session['es_diferencia'] = es_diferencia
    request.session.modified = True

    titulo = "Saldo pendiente" if es_diferencia else "Reserva Cancha"

    preference_data = {
        "items": [
            {
                "title": f"{titulo}: {reserva.cancha}",
                "description": (
                    f"Fecha: {reserva.fecha} - "
                    f"Horas: {', '.join(reserva.get_horas())} - "
                    f"Duración: {reserva.duracion_texto}"
                ),
                "quantity": 1,
                "currency_id": "COP",
                "unit_price": total,
            }
        ],
        "payer": {
            "email": usuario.email,
            "name": usuario.first_name or "Cliente",
            "surname": usuario.last_name or "CanchaFácil",
        },
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "external_reference": str(reserva.id),
        "metadata": {
            "reserva_id": str(reserva.id),
            "tipo_pago": tipo_pago,
            "monto_pagado": str(total),
            "es_diferencia": "1" if es_diferencia else "0",
        }
    }

    if not es_local:
        preference_data["auto_return"] = "approved"

    try:
        result = sdk.preference().create(preference_data)
        response = result.get('response', {})

        if 'id' not in response:
            error_msg = response.get('message', 'Error desconocido de Mercado Pago')
            return HttpResponse(
                f"Error de Mercado Pago: {error_msg}<br><br>"
                f"Respuesta: <pre>{json.dumps(response, indent=2, default=str)}</pre>",
                status=400
            )

        reserva.mp_preference_id = response['id']
        reserva.save()

        return redirect(response['init_point'])

    except Exception as e:
        return HttpResponse(f"Error al crear preferencia: {e}", status=400)


def pago_exitoso_mp(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    reserva = None

    if reserva_id:
        try:
            reserva = Reserva.objects.get(id=reserva_id)

            monto_esta_vez = _to_decimal(request.session.get('monto_pagado', 0))
            if monto_esta_vez <= 0:
                monto_esta_vez = max(
                    Decimal('0'),
                    (reserva.precio_total or reserva.calcular_total()) - (reserva.monto_pagado or Decimal('0'))
                )

            monto_ya_pagado = reserva.monto_pagado or Decimal('0')

            reserva.precio_total    = reserva.precio_total or reserva.calcular_total()
            reserva.monto_pagado    = monto_ya_pagado + monto_esta_vez
            reserva.saldo_pendiente = max(Decimal('0'), reserva.precio_total - reserva.monto_pagado)
            reserva.estado          = Reserva.ESTADO_CONFIRMADA
            reserva.metodo_pago     = 'Mercado Pago'
            reserva.numero_factura  = reserva.numero_factura or f"FAC-{reserva.id:06d}"
            reserva.save()

            if monto_ya_pagado == 0:
                enviar_correo_confirmacion(reserva)

        except Reserva.DoesNotExist:
            pass

    for key in ('reserva_pendiente_id', 'tipo_pago', 'monto_pagado', 'es_diferencia'):
        if key in request.session:
            del request.session[key]

    return render(request, 'pagos/exito.html', {'reserva': reserva})


def pago_cancelado_mp(request):
    return render(request, 'pagos/cancelado.html')


@csrf_exempt
def webhook_mercadopago(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)

        if data.get('type') != 'payment':
            return HttpResponse(status=200)

        payment_id = data.get('data', {}).get('id')
        if not payment_id:
            return HttpResponse(status=200)

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        payment_info = sdk.payment().get(payment_id)
        payment = payment_info.get('response', {})

        if payment.get('status') == 'approved':
            external_reference = payment.get('external_reference')
            transaction_amount = payment.get('transaction_amount')

            if external_reference and transaction_amount:
                try:
                    reserva = Reserva.objects.get(id=external_reference)

                    if reserva.estado == Reserva.ESTADO_CONFIRMADA and (reserva.saldo_pendiente or Decimal('0')) <= 0:
                        return HttpResponse(status=200)

                    monto_esta_vez  = _to_decimal(transaction_amount)
                    monto_ya_pagado = reserva.monto_pagado or Decimal('0')

                    reserva.precio_total    = reserva.precio_total or reserva.calcular_total()
                    reserva.monto_pagado    = monto_ya_pagado + monto_esta_vez
                    reserva.saldo_pendiente = max(Decimal('0'), reserva.precio_total - reserva.monto_pagado)
                    reserva.estado          = Reserva.ESTADO_CONFIRMADA
                    reserva.metodo_pago     = 'Mercado Pago'
                    reserva.numero_factura  = reserva.numero_factura or f"FAC-{reserva.id:06d}"
                    reserva.save()

                    if monto_ya_pagado == 0:
                        enviar_correo_confirmacion(reserva)

                except Reserva.DoesNotExist:
                    pass

    except json.JSONDecodeError:
        return HttpResponse(status=400)
    except Exception as e:
        print(f"Error en webhook Mercado Pago: {e}")

    return HttpResponse(status=200)