from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.serializers.json import DjangoJSONEncoder
from usuarios.models import Usuario
from gestion_canchas.models import Cancha
from contacto.models import Resena
from reservas.models import Reserva
import json


def panel_principal(request):
    reservas = Reserva.objects.all().order_by('-id')
    canchas = Cancha.objects.all()

    # NUEVO: se serializan canchas y reservas a JSON para que el
    # modal de "Editar Reserva" (JS) pueda usarlas como CANCHAS y
    # RESERVAS_BD sin necesidad de otra llamada al backend.
    #
    # AJUSTA los nombres de campo (c.nombre, c.precio, r.cancha,
    # r.fecha, r.hora) si en tus modelos reales se llaman distinto.
    canchas_json = json.dumps([
        {'nombre': c.nombre, 'precio': c.precio}
        for c in canchas
    ], cls=DjangoJSONEncoder)

    reservas_json = json.dumps([
        {
            'id': r.id,
            'cancha': r.cancha,
            'fecha': str(r.fecha),
            'hora': str(r.hora),
        }
        for r in reservas
    ], cls=DjangoJSONEncoder)

    return render(request, 'panel/panel_base.html', {
        'canchas':            canchas,
        'resenas_activas':    Resena.objects.filter(archivada=False).order_by('-fecha'),
        'resenas_archivadas': Resena.objects.filter(archivada=True).order_by('-fecha'),
        'reservas':           reservas,
        'total_reservas':     reservas.count(),
        'confirmadas':        reservas.filter(estado='Confirmada').count(),
        'pendientes':         reservas.filter(estado='Pendiente').count(),
        'canchas_json':       canchas_json,
        'reservas_json':      reservas_json,
    })


@require_POST
def aprobar_reserva(request, id):
    try:
        reserva = Reserva.objects.get(id=id)
        reserva.estado = 'Confirmada'
        reserva.save()
        return JsonResponse({'status': 'ok'})
    except Reserva.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)


@require_POST
def eliminar_reserva_admin(request, id):
    try:
        Reserva.objects.get(id=id).delete()
        return JsonResponse({'status': 'ok'})
    except Reserva.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)


# FIX: le faltaba @require_POST (las otras dos vistas del panel sí lo
# tienen). Sin esto, la vista aceptaba GET y podía romperse al intentar
# parsear request.body como JSON vacío.
@require_POST
def editar_reserva_admin(request, id):
    try:
        reserva = Reserva.objects.get(id=id)
        data = json.loads(request.body.decode("utf-8"))
        reserva.nombre   = data.get("nombre",   reserva.nombre)
        reserva.correo   = data.get("correo",   reserva.correo)
        reserva.telefono = data.get("telefono", reserva.telefono)
        if data.get("fecha"):
            reserva.fecha = data["fecha"]
        if data.get("hora"):
            reserva.hora = data["hora"]
        reserva.cancha   = data.get("cancha",   reserva.cancha)
        reserva.duracion = data.get("duracion", reserva.duracion)
        # Campo exclusivo de administrador: el usuario final no tiene
        # acceso a este endpoint (namespace /panel_admin/...), así que
        # solo el admin puede llegar hasta aquí y cambiar el estado.
        reserva.estado   = data.get("estado",   reserva.estado)
        reserva.save()
        return JsonResponse({'status': 'ok'})
    except Reserva.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)