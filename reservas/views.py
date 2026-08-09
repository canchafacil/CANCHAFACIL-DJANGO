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

    # Una reserva "activa" bloquea nuevas reservas (pendiente o confirmada, no vencida)
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

        # Bloqueo: no permitir una segunda reserva activa
        ya_tiene_activa = Reserva.objects.filter(
            correo=usuario.email,
            estado__in=[Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA],
        ).exists()
        if ya_tiene_activa:
            return JsonResponse(
                {"status": "error", "mensaje": "Ya tienes una reserva activa."},
                status=409
            )

        data = json.loads(request.body.decode("utf-8"))

        # Bloqueo: que la hora/fecha/cancha no se haya ocupado justo antes de confirmar
        conflicto = Reserva.objects.filter(
            cancha=data["cancha"],
            fecha=data["fecha"],
            hora=data["hora"],
        ).exclude(estado=Reserva.ESTADO_CANCELADA).exists()
        if conflicto:
            return JsonResponse(
                {"status": "error", "mensaje": "Esa fecha/hora ya está ocupada."},
                status=409
            )

        reserva = Reserva.objects.create(
            nombre   = f"{usuario.first_name} {usuario.last_name}".strip(),
            correo   = usuario.email,
            telefono = usuario.phone,
            fecha    = data["fecha"],
            hora     = data["hora"],
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
        reserva.nombre   = data.get("nombre",   reserva.nombre)
        reserva.correo   = data.get("correo",   reserva.correo)
        reserva.telefono = data.get("telefono", reserva.telefono)
        reserva.fecha    = data.get("fecha",    reserva.fecha)
        reserva.hora     = data.get("hora",     reserva.hora)
        reserva.cancha   = data.get("cancha",   reserva.cancha)
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
    reserva.metodo_pago = data.get("metodo_pago", "Simulado")
    reserva.precio_total = reserva.calcular_total()
    reserva.numero_factura = f"FAC-{reserva.id:06d}"
    reserva.estado = Reserva.ESTADO_CONFIRMADA
    reserva.save()

    enviar_correo_confirmacion(reserva)

    del request.session["reserva_pendiente_id"]

    return JsonResponse({"status": "ok", "mensaje": "Pago confirmado y correo enviado"})


def enviar_correo_confirmacion(reserva):
    asunto = f"Confirmación de tu reserva - {settings.EMPRESA_NOMBRE}"
    contexto = {"reserva": reserva}

    cuerpo_html = render_to_string("reservas/confirmacion_reserva.html", contexto)
    cuerpo_texto = (
        f"Hola {reserva.nombre},\n\n"
        f"Tu reserva ha sido confirmada:\n"
        f"Cancha: {reserva.cancha}\n"
        f"Fecha: {reserva.fecha}\n"
        f"Hora: {reserva.hora}\n"
        f"Duración: {reserva.duracion}\n"
        f"Total pagado: ${reserva.precio_total}\n"
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

    reserva.fecha    = request.POST.get('fecha', reserva.fecha)
    reserva.hora     = request.POST.get('hora', reserva.hora)
    reserva.cancha   = request.POST.get('cancha', reserva.cancha)
    reserva.duracion = request.POST.get('duracion', reserva.duracion)
    reserva.save()

    return redirect('perfil')


# NOTA: eliminar_reserva_perfil se eliminó a propósito. Ya no existe forma
# de borrar una reserva desde el perfil del usuario.