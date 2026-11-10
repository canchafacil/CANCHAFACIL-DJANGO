import json
import logging
import mercadopago
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import Reserva
from usuarios.models import Usuario
from gestion_canchas.models import Cancha
from pagos.services import consultar_pago, registrar_pago_aprobado, monto_esperado

logger = logging.getLogger(__name__)


# =================================================================
# CONSTANTES Y FUNCIONES AUXILIARES
# =================================================================

HORAS_VALIDAS = [
    '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
    '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
    '18:00', '19:00', '20:00', '21:00', '22:00'
]


def _horas_son_consecutivas(horas):
    """Valida que las horas sean consecutivas y sin duplicados."""
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
    """Sincroniza el estado de cada reserva (confirmada -> completada si ya pasó)."""
    for r in queryset:
        r.sincronizar_estado()


def _horas_ocupadas(cancha, fecha, excluir_id=None):
    """Devuelve un set con todas las horas ocupadas para una cancha+fecha."""
    qs = Reserva.objects.filter(cancha=cancha, fecha=fecha).exclude(estado=Reserva.ESTADO_CANCELADA)
    if excluir_id is not None:
        qs = qs.exclude(id=excluir_id)

    ocupadas = set()
    for r in qs:
        ocupadas.update(r.get_horas())
    return ocupadas


# =================================================================
# VISTAS PRINCIPALES (reservas, creación, edición, perfil)
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

    tiene_reserva_activa = False
    if usuario:
        tiene_reserva_activa = Reserva.objects.filter(
            correo=usuario.email,
            estado__in=[Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA],
        ).exists()

    return render(request, "reservas/formulario.html", {
        "reservas": todas,
        "canchas": canchas,
        "usuario": usuario,
        "cancha_id": cancha_id,
        "tiene_reserva_activa": tiene_reserva_activa,
    })


@require_POST
def crear_reserva(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return JsonResponse({"status": "error", "mensaje": "Debes iniciar sesión", "redirect": "login"}, status=401)

    try:
        usuario = Usuario.objects.get(id=usuario_id)

        ya_tiene_activa = Reserva.objects.filter(
            correo=usuario.email,
            estado__in=[Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA],
        ).exists()
        if ya_tiene_activa:
            return JsonResponse(
                {"status": "error", "mensaje": "Ya tienes una reserva pendiente o confirmada."},
                status=409
            )

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
        conflicto = any(h in ocupadas for h in horas_solicitadas)
        if conflicto:
            return JsonResponse(
                {"status": "error", "mensaje": "Una o más horas seleccionadas ya están ocupadas."},
                status=409
            )

        Reserva.objects.filter(
            correo=usuario.email,
            estado=Reserva.ESTADO_PENDIENTE,
        ).update(estado=Reserva.ESTADO_CANCELADA)

        horas_ordenadas = sorted(horas_solicitadas)

        reserva = Reserva.objects.create(
            nombre   = f"{usuario.first_name} {usuario.last_name}".strip(),
            correo   = usuario.email,
            telefono = usuario.phone,
            fecha    = data["fecha"],
            hora     = horas_ordenadas[0],
            horas    = horas_ordenadas,
            cancha   = data["cancha"],
            duracion = data["duracion"],
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
        conflicto = any(h in ocupadas for h in horas_nuevas)
        if conflicto:
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
        reserva.duracion = data.get("duracion", reserva.duracion)
        reserva.save()
        return JsonResponse({"status": "ok"})
    except Reserva.DoesNotExist:
        return JsonResponse({"status": "error", "mensaje": "Reserva no encontrada"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)


@require_POST
def cancelar_reserva_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=id)

    if reserva.correo != usuario.email:
           return redirect('usuarios:perfil')

    reserva.sincronizar_estado()

    # Antes usaba reserva.puede_editarse, que también exige que la
    # fecha/hora no haya pasado. Cancelar no debería depender de eso:
    # solo importa que la reserva siga en un estado cancelable.
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


def pago(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    reserva = None
    total = 0

    if reserva_id:
        try:
            reserva = Reserva.objects.get(id=reserva_id)
            total = float(reserva.calcular_total())
        except Reserva.DoesNotExist:
            pass

    return render(request, "pagos/pago.html", {
        "reserva": reserva,
        "total": total,
        "retorno": request.GET.get("collection_status") or request.GET.get("status") or "",
    })


@require_POST
def confirmar_pago(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    if not reserva_id:
        return JsonResponse({"status": "error", "mensaje": "No hay reserva pendiente"}, status=400)

    reserva = get_object_or_404(Reserva, id=reserva_id)
    data = json.loads(request.body.decode("utf-8")) if request.body else {}

    tipo_pago = data.get("tipo_pago", Reserva.TIPO_PAGO_COMPLETO)
    if tipo_pago not in (Reserva.TIPO_PAGO_COMPLETO, Reserva.TIPO_PAGO_ABONO):
        return JsonResponse({"status": "error", "mensaje": "Tipo de pago inválido"}, status=400)

    total = reserva.calcular_total()
    monto_a_pagar = reserva.calcular_abono_50() if tipo_pago == Reserva.TIPO_PAGO_ABONO else total

    reserva.metodo_pago = data.get("metodo_pago", "Simulado")
    reserva.precio_total = total
    reserva.tipo_pago = tipo_pago
    reserva.monto_pagado = monto_a_pagar
    reserva.saldo_pendiente = total - monto_a_pagar
    reserva.numero_factura = f"FAC-{reserva.id:06d}"
    reserva.estado = Reserva.ESTADO_CONFIRMADA
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
    if reserva.tipo_pago == Reserva.TIPO_PAGO_ABONO:
        linea_pago = (
            f"Abonaste: ${reserva.monto_pagado} (50%)\n"
            f"Saldo pendiente a pagar en la cancha: ${reserva.saldo_pendiente}"
        )

    cuerpo_texto = (
        f"Hola {reserva.nombre},\n\n"
        f"Tu reserva ha sido confirmada:\n"
        f"Cancha: {reserva.cancha}\n"
        f"Fecha: {reserva.fecha}\n"
        f"Hora(s): {horas_texto}\n"
        f"Duración: {reserva.duracion}\n"
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


# ---------------------------------------------------------------------
# Vistas para el PERFIL del usuario
# ---------------------------------------------------------------------

@require_POST
def editar_reserva_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=id)

    if reserva.correo != usuario.email:
           return redirect('usuarios:perfil')

    reserva.sincronizar_estado()

    if not reserva.puede_editarse:
           return redirect('usuarios:perfil')

    nueva_fecha  = request.POST.get('fecha', str(reserva.fecha))
    nueva_hora   = request.POST.get('hora', reserva.hora.strftime('%H:%M'))
    nueva_cancha = request.POST.get('cancha', reserva.cancha)

    reserva.fecha    = nueva_fecha
    reserva.hora     = nueva_hora
    reserva.horas    = [nueva_hora]
    reserva.cancha   = nueva_cancha
    reserva.duracion = request.POST.get('duracion', reserva.duracion)
    reserva.save()

    return redirect('usuarios:perfil')


# =================================================================
# VISTAS PARA MERCADO PAGO
# =================================================================

@csrf_exempt
def crear_preferencia_mercadopago(request, reserva_id):
    """
    Crea una preferencia de pago en Mercado Pago y redirige al usuario.
    El monto SIEMPRE se calcula en el servidor.

    - En local (127.0.0.1/localhost): URLs con http://, sin auto_return ni webhook.
    - En ngrok/producción: URLs con https://, con auto_return y notification_url.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    reserva = get_object_or_404(Reserva, id=reserva_id)
    usuario = get_object_or_404(Usuario, id=request.session['usuario_id'])

    if reserva.correo != usuario.email:
           return redirect('usuarios:perfil')

    if reserva.estado == 'confirmada':
        return redirect('pago_exitoso_mp')

    

    # Configurar SDK
    token = settings.MERCADOPAGO_ACCESS_TOKEN
    logger.warning("MP token: prefijo=%r largo=%s", token[:9], len(token))
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    # Tipo de pago validado; el monto se calcula en el servidor
    tipo_pago = request.POST.get('tipo_pago', 'completo')
    if tipo_pago not in ('completo', 'abono'):
        tipo_pago = 'completo'
    reserva.tipo_pago = tipo_pago
    total = int(monto_esperado(reserva))

    # Detectar si estamos en local o en ngrok
    dominio = request.build_absolute_uri('/').rstrip('/')
    es_local = ('127.0.0.1' in dominio) or ('localhost' in dominio)

    success_url = request.build_absolute_uri(reverse('pago_exitoso_mp'))
    failure_url = request.build_absolute_uri(reverse('pago_cancelado_mp'))
    pending_url = failure_url

    try:
        notification_url = request.build_absolute_uri(reverse('webhook_mercadopago'))
    except NoReverseMatch:
        notification_url = None
        logger.warning("No existe la URL con nombre 'webhook_mercadopago'; no se enviará notification_url")

    # Si NO es local, forzar https:// (Mercado Pago lo exige para auto_return)
    if not es_local:
        success_url = success_url.replace('http://', 'https://')
        failure_url = failure_url.replace('http://', 'https://')
        pending_url = pending_url.replace('http://', 'https://')
        if notification_url:
            notification_url = notification_url.replace('http://', 'https://')

    request.session['reserva_pendiente_id'] = reserva.id
    request.session.modified = True

    # Armar preferencia
    preference_data = {
        "items": [
            {
                "title": f"Reserva Cancha: {reserva.cancha}",
                "description": (
                    f"Fecha: {reserva.fecha} - "
                    f"Horas: {', '.join(reserva.get_horas())} - "
                    f"Duración: {reserva.duracion}"
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
        }
    }

    # Solo agregar auto_return y webhook cuando NO estamos en local
    if not es_local:
        preference_data["auto_return"] = "approved"
        if notification_url:
            preference_data["notification_url"] = notification_url

    # Crear preferencia en Mercado Pago
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
        reserva.save(update_fields=['mp_preference_id', 'tipo_pago'])

        return redirect(response['init_point'])

    except Exception as e:
        return HttpResponse(f"Error al crear preferencia: {e}", status=400)


def pago_exitoso_mp(request):
    """Retorno de Mercado Pago: verifica el pago con la API, no confía en la URL."""
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    reserva = None

    if payment_id:
        reserva = registrar_pago_aprobado(consultar_pago(payment_id))

    # Si el webhook llegó primero (o no vino payment_id), usa la sesión
    if reserva is None:
        reserva_id = request.session.get('reserva_pendiente_id')
        if reserva_id:
            reserva = Reserva.objects.filter(id=reserva_id).first()

    if reserva and reserva.estado == Reserva.ESTADO_CONFIRMADA:
        request.session.pop('reserva_pendiente_id', None)
        return render(request, 'pagos/exito.html', {'reserva': reserva})

    # No hay pago aprobado verificado
    return render(request, 'pagos/cancelado.html', {'reserva': reserva})


def pago_cancelado_mp(request):
    """Vista a la que Mercado Pago redirige si el usuario cancela o el pago falla."""
    reserva_id = request.session.get('reserva_pendiente_id')
    reserva = Reserva.objects.filter(id=reserva_id).first() if reserva_id else None
    return render(request, 'pagos/cancelado.html', {'reserva': reserva})


@csrf_exempt
def webhook_mercadopago(request):
    """Webhook para notificaciones de Mercado Pago."""
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        try:
            data = json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            data = {}

        tipo = data.get('type') or request.GET.get('type') or request.GET.get('topic')
        if tipo != 'payment':
            return HttpResponse(status=200)

        payment_id = (data.get('data') or {}).get('id') or request.GET.get('data.id')
        if not payment_id:
            return HttpResponse(status=200)

        registrar_pago_aprobado(consultar_pago(payment_id))
        return HttpResponse(status=200)

    except Exception:
        logger.exception("Error en webhook Mercado Pago")
        return HttpResponse(status=500)  # MP reintenta