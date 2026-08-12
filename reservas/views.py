from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import json
from .models import Reserva
from usuarios.models import Usuario
from gestion_canchas.models import Cancha


def _sincronizar_todas(queryset):
    """Recorre un queryset y sincroniza el estado de cada reserva (confirmada -> completada si ya pasó)."""
    for r in queryset:
        r.sincronizar_estado()


def _horas_ocupadas(cancha, fecha, excluir_id=None):
    """
    Devuelve un set con TODAS las horas 'HH:MM' ocupadas para una cancha+fecha,
    considerando el campo 'horas' (o 'hora' como fallback para reservas viejas).
    Ignora reservas canceladas.
    """
    qs = Reserva.objects.filter(cancha=cancha, fecha=fecha).exclude(estado=Reserva.ESTADO_CANCELADA)
    if excluir_id is not None:
        qs = qs.exclude(id=excluir_id)

    ocupadas = set()
    for r in qs:
        ocupadas.update(r.get_horas())
    return ocupadas


def pagina_reservas(request):
    return render(request, "reservas/reservas.html")


def reservas(request, cancha_id=None):
    todas = Reserva.objects.all().order_by('-id')
    _sincronizar_todas(todas)  # actualiza estados vencidos antes de mostrar el calendario

    canchas = Cancha.objects.filter(disponible=True)

    usuario = None
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        usuario = Usuario.objects.filter(id=usuario_id).first()

    # Una reserva "activa" bloquea nuevas reservas: solo la CONFIRMADA (ya
    # pagada) bloquea de verdad. Las PENDIENTES (nunca pagadas) ya no
    # cuentan aquí porque crear_reserva las cancela automáticamente.
    tiene_reserva_activa = False
    if usuario:
        tiene_reserva_activa = Reserva.objects.filter(
            correo=usuario.email,
            estado=Reserva.ESTADO_CONFIRMADA,
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

        # Bloqueo real: solo una reserva CONFIRMADA (ya pagada) impide
        # crear una nueva. Las reservas PENDIENTES (carritos abandonados,
        # nunca pagados) se cancelan automáticamente más abajo en vez de
        # bloquear, para que no se queden atascadas para siempre.
        ya_tiene_confirmada = Reserva.objects.filter(
            correo=usuario.email,
            estado=Reserva.ESTADO_CONFIRMADA,
        ).exists()
        if ya_tiene_confirmada:
            return JsonResponse(
                {"status": "error", "mensaje": "Ya tienes una reserva confirmada."},
                status=409
            )

        data = json.loads(request.body.decode("utf-8"))

        # Lista de horas seleccionadas (el JS manda "horas": [...]).
        # Fallback a "hora" solo por compatibilidad si algo manda una sola.
        horas_solicitadas = data.get("horas") or [data["hora"]]
        if not isinstance(horas_solicitadas, list) or len(horas_solicitadas) == 0:
            return JsonResponse({"status": "error", "mensaje": "Debes seleccionar al menos una hora."}, status=400)

        # Bloqueo: si CUALQUIERA de las horas solicitadas ya está ocupada
        ocupadas = _horas_ocupadas(data["cancha"], data["fecha"])
        conflicto = any(h in ocupadas for h in horas_solicitadas)
        if conflicto:
            return JsonResponse(
                {"status": "error", "mensaje": "Una o más horas seleccionadas ya están ocupadas."},
                status=409
            )

        # Cancela automáticamente cualquier reserva PENDIENTE anterior de
        # este usuario (carritos abandonados que nunca se pagaron), para
        # que no queden atascados bloqueando la sesión de pago.
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
                {"status": "error", "mensaje": "Esta reserva ya no se puede editar (está completada, cancelada o ya pasó su fecha)."},
                status=403
            )

        data = json.loads(request.body.decode("utf-8"))

        nueva_fecha  = data.get("fecha", str(reserva.fecha))
        nueva_cancha = data.get("cancha", reserva.cancha)
        horas_nuevas = data.get("horas") or [data.get("hora", reserva.hora.strftime('%H:%M'))]

        if not isinstance(horas_nuevas, list) or len(horas_nuevas) == 0:
            return JsonResponse({"status": "error", "mensaje": "Debes seleccionar al menos una hora."}, status=400)

        # Bloqueo: verificar conflictos EXCLUYENDO esta misma reserva
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


# NOTA: eliminar_reserva y eliminar_reserva_perfil se eliminaron a propósito.
# Ninguna reserva se puede borrar nunca, sin excepción.

@require_POST
def cancelar_reserva_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login_admin')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=id)

    if reserva.correo != usuario.email:
        return redirect('perfil')

    reserva.sincronizar_estado()

    # Solo se puede cancelar si todavía se podría editar
    # (pendiente/confirmada y la fecha no ha pasado)
    if reserva.puede_editarse:
        reserva.estado = Reserva.ESTADO_CANCELADA
        reserva.save(update_fields=['estado'])

    return redirect('perfil')


def pago(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    reserva = None
    if reserva_id:
        try:
            reserva = Reserva.objects.get(id=reserva_id)
        except Reserva.DoesNotExist:
            pass
    return render(request, "pagos/pago.html", {"reserva": reserva})


@require_POST
def confirmar_pago(request):
    reserva_id = request.session.get("reserva_pendiente_id")
    if not reserva_id:
        return JsonResponse({"status": "error", "mensaje": "No hay reserva pendiente"}, status=400)

    reserva = get_object_or_404(Reserva, id=reserva_id)

    data = json.loads(request.body.decode("utf-8")) if request.body else {}

    # tipo_pago: "completo" o "abono" (viene de los botones que elige el usuario)
    tipo_pago = data.get("tipo_pago", Reserva.TIPO_PAGO_COMPLETO)
    if tipo_pago not in (Reserva.TIPO_PAGO_COMPLETO, Reserva.TIPO_PAGO_ABONO):
        return JsonResponse({"status": "error", "mensaje": "Tipo de pago inválido"}, status=400)

    total = reserva.calcular_total()

    if tipo_pago == Reserva.TIPO_PAGO_ABONO:
        monto_a_pagar = reserva.calcular_abono_50()
    else:
        monto_a_pagar = total

    reserva.metodo_pago = data.get("metodo_pago", "Simulado")
    reserva.precio_total = total
    reserva.tipo_pago = tipo_pago
    reserva.monto_pagado = monto_a_pagar
    reserva.saldo_pendiente = total - monto_a_pagar
    reserva.numero_factura = f"FAC-{reserva.id:06d}"
    reserva.estado = Reserva.ESTADO_CONFIRMADA
    reserva.save()

    enviar_correo_confirmacion(reserva)

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
        return redirect('login_admin')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=id)

    if reserva.correo != usuario.email:
        return redirect('perfil')

    reserva.sincronizar_estado()

    if not reserva.puede_editarse:
        # No se puede editar: se ignora el intento y se vuelve al perfil.
        return redirect('perfil')

    nueva_fecha  = request.POST.get('fecha', str(reserva.fecha))
    nueva_hora   = request.POST.get('hora', reserva.hora.strftime('%H:%M'))
    nueva_cancha = request.POST.get('cancha', reserva.cancha)

    reserva.fecha    = nueva_fecha
    reserva.hora     = nueva_hora
    reserva.horas    = [nueva_hora]  # este formulario simple solo maneja una hora
    reserva.cancha   = nueva_cancha
    reserva.duracion = request.POST.get('duracion', reserva.duracion)
    reserva.save()

    return redirect('perfil')


# NOTA: eliminar_reserva_perfil se eliminó a propósito. Ya no existe forma
# de borrar una reserva desde el perfil del usuario.