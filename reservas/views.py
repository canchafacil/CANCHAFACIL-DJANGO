from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import json
from .models import Reserva


def pagina_reservas(request):
    return render(request, "reservas/reservas.html")


def reservas(request):
    todas = Reserva.objects.all().order_by('-id')
    return render(request, "reservas/formulario.html", {"reservas": todas})


@require_POST
def crear_reserva(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        reserva = Reserva.objects.create(
            nombre   = data["nombre"],
            correo   = data["correo"],
            telefono = data["telefono"],
            fecha    = data["fecha"],
            hora     = data["hora"],
            cancha   = data["cancha"],
            duracion = data["duracion"],
        )
        # Todavía NO se envía correo: la reserva está "Pendiente" hasta que se pague
        request.session["reserva_pendiente_id"] = reserva.id

        return JsonResponse({"status": "ok", "id": reserva.id})
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "mensaje": "Datos inválidos"}, status=400)


@require_POST
def editar_reserva(request, id):
    try:
        reserva = Reserva.objects.get(id=id)
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


@require_POST
def eliminar_reserva(request, id):
    reserva = get_object_or_404(Reserva, id=id)
    reserva.delete()
    return redirect("reservas")


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
    """
    Vista de PRUEBA: simula que el pago fue exitoso.
    Cuando integres la pasarela real, esta lógica va en el webhook/callback
    de confirmación de esa pasarela (reemplazando el simulado por la real).
    """
    reserva_id = request.session.get("reserva_pendiente_id")
    if not reserva_id:
        return JsonResponse({"status": "error", "mensaje": "No hay reserva pendiente"}, status=400)

    reserva = get_object_or_404(Reserva, id=reserva_id)

    # --- Datos simulados de pago (acá irían los reales de la pasarela) ---
    data = json.loads(request.body.decode("utf-8")) if request.body else {}
    reserva.metodo_pago = data.get("metodo_pago", "Simulado")
    reserva.precio_total = reserva.calcular_total()
    reserva.numero_factura = f"FAC-{reserva.id:06d}"
    reserva.estado = "Confirmada"
    reserva.save()

    enviar_correo_confirmacion(reserva)

    # Limpiamos la sesión: ya no queda pendiente
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