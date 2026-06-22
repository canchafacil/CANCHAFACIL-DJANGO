from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import Reserva


def reservas(request):
    todas = Reserva.objects.all().order_by('-id')
    return render(request, "reservas/formulario.html", {"reservas": todas})


def crear_reserva(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))

        Reserva.objects.create(
            nombre=data["nombre"],
            correo=data["correo"],
            telefono=data["telefono"],
            fecha=data["fecha"],
            hora=data["hora"],
            cancha=data["cancha"],
            duracion=data["duracion"],
        )

        return JsonResponse({"status": "ok"})


@require_POST
def editar_reserva(request, id):
    data = json.loads(request.body.decode("utf-8"))

    reserva = get_object_or_404(Reserva, id=id)

    reserva.nombre = data.get("nombre", reserva.nombre)
    reserva.correo = data.get("correo", reserva.correo)
    reserva.telefono = data.get("telefono", reserva.telefono)
    reserva.fecha = data.get("fecha", reserva.fecha)
    reserva.hora = data.get("hora", reserva.hora)
    reserva.cancha = data.get("cancha", reserva.cancha)
    reserva.duracion = data.get("duracion", reserva.duracion)

    reserva.save()

    return JsonResponse({"status": "ok"})


@require_POST
def eliminar_reserva(request, id):
    reserva = get_object_or_404(Reserva, id=id)
    reserva.delete()
    return redirect("reservas")


def pago(request):
    return render(request, "paginas/pago.html")
@require_POST
def editar_reserva(request, id):
    try:
        reserva = Reserva.objects.get(id=id)
        data = json.loads(request.body.decode("utf-8"))

        reserva.nombre = data.get("nombre", reserva.nombre)
        reserva.correo = data.get("correo", reserva.correo)
        reserva.telefono = data.get("telefono", reserva.telefono)
        reserva.fecha = data.get("fecha", reserva.fecha)
        reserva.hora = data.get("hora", reserva.hora)
        reserva.cancha = data.get("cancha", reserva.cancha)
        reserva.duracion = data.get("duracion", reserva.duracion)

        reserva.save()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)