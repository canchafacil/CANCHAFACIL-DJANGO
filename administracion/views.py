from datetime import timedelta
from calendar import monthrange
import re

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.db.models import Sum, Count

from usuarios.models import Usuario
from gestion_canchas.models import Cancha
from contacto.models import Resena, MensajeContacto
from reservas.models import Reserva
from .reportes import generar_reporte_general, generar_reporte_mes_actual
import json
from django.core.mail import send_mail
from django.conf import settings


ESTADOS_PAGADOS = [Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_COMPLETADA]
DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

# Debe coincidir exactamente con el array HORAS del template panel_reservas.html
HORAS_DISPONIBLES = ['06:00', '07:00', '08:00', '09:00', '10:00', '11:00', '12:00',
                      '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00']


def _contexto_ingresos_mes():
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    ultimo_dia = monthrange(hoy.year, hoy.month)[1]
    fin_mes = hoy.replace(day=ultimo_dia)

    reservas_mes = Reserva.objects.filter(
        fecha__range=(inicio_mes, fin_mes),
        estado__in=ESTADOS_PAGADOS,
    )

    total_mes = reservas_mes.aggregate(total=Sum('monto_pagado'))['total'] or 0
    cantidad_pagadas = reservas_mes.count()
    dias_transcurridos = hoy.day
    promedio_diario = round(total_mes / dias_transcurridos) if dias_transcurridos else 0

    ingresos_por_dia_semana = {i: 0 for i in range(7)}
    for r in reservas_mes:
        ingresos_por_dia_semana[r.fecha.weekday()] += float(r.monto_pagado)
    mejor_dia = DIAS_SEMANA[max(ingresos_por_dia_semana, key=ingresos_por_dia_semana.get)] if total_mes else '—'

    reservas_activas = Reserva.objects.filter(
        estado=Reserva.ESTADO_CONFIRMADA,
        fecha__gte=hoy,
    ).order_by('fecha', 'hora')[:10]

    transacciones = Reserva.objects.all().order_by('-fecha', '-hora')[:15]

    return {
        'total_mes': total_mes,
        'cantidad_pagadas': cantidad_pagadas,
        'promedio_diario': promedio_diario,
        'mejor_dia': mejor_dia,
        'reservas_activas': reservas_activas,
        'transacciones': transacciones,
    }


def _contexto_mensajes_contacto():
    return {
        'mensajes_contacto': MensajeContacto.objects.all().order_by('respondido', '-fecha'),
        'mensajes_sin_responder': MensajeContacto.objects.filter(respondido=False).count(),
    }


def _contexto_estados_reservas():
    """Conteo real de reservas por estado, para la tarjeta 'Panel Contable'."""
    conteo = Reserva.objects.values('estado').annotate(total=Count('id'))
    mapa = {c['estado']: c['total'] for c in conteo}

    return {
        'total_confirmadas': mapa.get(Reserva.ESTADO_CONFIRMADA, 0),
        'total_pendientes': mapa.get(Reserva.ESTADO_PENDIENTE, 0),
        'total_completadas': mapa.get(Reserva.ESTADO_COMPLETADA, 0),
        'total_canceladas': mapa.get(Reserva.ESTADO_CANCELADA, 0),
    }


def _contexto_cancha_top():
    """Cancha con más reservas (excluyendo canceladas) y el cliente más frecuente."""
    top_cancha = (
        Reserva.objects
        .exclude(estado=Reserva.ESTADO_CANCELADA)
        .values('cancha')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )

    top_cliente = (
        Reserva.objects
        .exclude(estado=Reserva.ESTADO_CANCELADA)
        .values('nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )

    return {
        'cancha_top_nombre': top_cancha['cancha'] if top_cancha else '—',
        'cancha_top_total': top_cancha['total'] if top_cancha else 0,
        'cliente_top_nombre': top_cliente['nombre'] if top_cliente else '—',
        'cliente_top_total': top_cliente['total'] if top_cliente else 0,
    }


def ingresos_chart_data(request):
    hoy = timezone.localdate()

    inicio_semana = hoy - timedelta(days=hoy.weekday())
    labels_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    valores_semana = [0] * 7
    for r in Reserva.objects.filter(
        fecha__range=(inicio_semana, inicio_semana + timedelta(days=6)),
        estado__in=ESTADOS_PAGADOS,
    ):
        valores_semana[r.fecha.weekday()] += float(r.monto_pagado)

    ultimo_dia = monthrange(hoy.year, hoy.month)[1]
    labels_mes = [str(d) for d in range(1, ultimo_dia + 1)]
    valores_mes = [0] * ultimo_dia
    for r in Reserva.objects.filter(fecha__year=hoy.year, fecha__month=hoy.month, estado__in=ESTADOS_PAGADOS):
        valores_mes[r.fecha.day - 1] += float(r.monto_pagado)

    labels_año = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    valores_año = [0] * 12
    for r in Reserva.objects.filter(fecha__year=hoy.year, estado__in=ESTADOS_PAGADOS):
        valores_año[r.fecha.month - 1] += float(r.monto_pagado)

    return JsonResponse({
        'semana': {'labels': labels_semana, 'valores': valores_semana},
        'mes': {'labels': labels_mes, 'valores': valores_mes},
        'año': {'labels': labels_año, 'valores': valores_año},
    })


def panel_principal(request):
    for r in Reserva.objects.filter(estado=Reserva.ESTADO_CONFIRMADA):
        r.sincronizar_estado()

    reservas = Reserva.objects.all().order_by('-id')
    canchas = Cancha.objects.all()

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

    context = {
        'canchas':            canchas,
        'resenas_activas':    Resena.objects.filter(archivada=False).order_by('-fecha'),
        'resenas_archivadas': Resena.objects.filter(archivada=True).order_by('-fecha'),
        'reservas':           reservas,
        'total_reservas':     reservas.count(),
        'confirmadas':        reservas.filter(estado=Reserva.ESTADO_CONFIRMADA).count(),
        'pendientes':         reservas.filter(estado=Reserva.ESTADO_PENDIENTE).count(),
        'canchas_json':       canchas_json,
        'reservas_json':      reservas_json,
    }

    context.update(_contexto_ingresos_mes())
    context.update(_contexto_mensajes_contacto())
    context.update(_contexto_estados_reservas())
    context.update(_contexto_cancha_top())

    return render(request, 'panel/panel_base.html', context)


@require_POST
def aprobar_reserva(request, id):
    try:
        reserva = Reserva.objects.get(id=id)
        reserva.estado = Reserva.ESTADO_CONFIRMADA
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
        reserva.estado   = data.get("estado",   reserva.estado)
        reserva.save()
        return JsonResponse({'status': 'ok'})
    except Reserva.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)


@require_POST
def crear_reserva_admin(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

        reserva = Reserva(
            nombre=data.get("nombre", ""),
            correo=data.get("correo", ""),
            telefono=data.get("telefono", ""),
            fecha=data.get("fecha"),
            hora=data.get("hora"),
            cancha=data.get("cancha", ""),
            duracion=data.get("duracion"),
            estado=data.get("estado", Reserva.ESTADO_PENDIENTE),
        )

        if hasattr(reserva, "monto_pagado") and data.get("monto_pagado") is not None:
            reserva.monto_pagado = data["monto_pagado"]

        reserva.save()
        return JsonResponse({'status': 'ok', 'id': reserva.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)


def _horas_ocupadas_por_reserva(r):
    """Lista de horas ('HH:MM') que cubre una reserva, a partir de su hora
    de inicio y el texto de duración (ej: '2 Horas')."""
    hora_str = r.hora.strftime('%H:%M') if hasattr(r.hora, 'strftime') else str(r.hora)[:5]
    if hora_str not in HORAS_DISPONIBLES:
        return []
    idx = HORAS_DISPONIBLES.index(hora_str)
    match = re.search(r'\d+', r.duracion or '')
    cantidad = int(match.group()) if match else 1
    return HORAS_DISPONIBLES[idx: idx + cantidad]


def horas_ocupadas(request):
    """AJAX: horas ya reservadas para una cancha+fecha (excluyendo, opcionalmente,
    la reserva que se está editando)."""
    cancha = request.GET.get('cancha')
    fecha = request.GET.get('fecha')
    excluir_id = request.GET.get('excluir_id')

    if not cancha or not fecha:
        return JsonResponse({'status': 'error', 'mensaje': 'Faltan parámetros cancha/fecha'}, status=400)

    reservas = Reserva.objects.filter(
        cancha=cancha,
        fecha=fecha,
    ).exclude(estado=Reserva.ESTADO_CANCELADA)

    if excluir_id:
        reservas = reservas.exclude(id=excluir_id)

    ocupadas = []
    for r in reservas:
        ocupadas.extend(_horas_ocupadas_por_reserva(r))

    return JsonResponse({'status': 'ok', 'ocupadas': sorted(set(ocupadas))})


def resumen_reservas_mes(request):
    """AJAX: cuántas horas hay reservadas por día en un mes (para pintar los
    puntos naranjas del mini-calendario)."""
    anio = request.GET.get('anio')
    mes = request.GET.get('mes')
    cancha = request.GET.get('cancha')

    if not anio or not mes:
        return JsonResponse({'status': 'error', 'mensaje': 'Faltan parámetros anio/mes'}, status=400)

    reservas = Reserva.objects.filter(
        fecha__year=anio,
        fecha__month=mes,
    ).exclude(estado=Reserva.ESTADO_CANCELADA)

    if cancha:
        reservas = reservas.filter(cancha=cancha)

    resumen = {}
    for r in reservas:
        dia = r.fecha.day
        cantidad_horas = len(_horas_ocupadas_por_reserva(r)) or 1
        resumen[dia] = resumen.get(dia, 0) + cantidad_horas

    return JsonResponse({'status': 'ok', 'resumen': resumen})


@require_POST
def marcar_mensaje_respondido(request, id):
    try:
        msg = MensajeContacto.objects.get(id=id)
        msg.respondido = True
        msg.save()
        return JsonResponse({'status': 'ok'})
    except MensajeContacto.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
    

@require_POST
def responder_mensaje(request, id):
    try:
        msg = MensajeContacto.objects.get(id=id)
    except MensajeContacto.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
 
    respuesta = request.POST.get('respuesta', '').strip()
    if not respuesta:
        return JsonResponse({'status': 'error', 'mensaje': 'La respuesta no puede estar vacía'}, status=400)
 
    send_mail(
        f'Respuesta a tu mensaje: {msg.asunto} - CanchaFácil',
        f'''
Hola {msg.nombre}
 
Este es un mensaje de nuestro equipo de CanchaFácil en respuesta a tu consulta:
 
"{msg.mensaje}"
 
Nuestra respuesta:
{respuesta}
        ''',
        settings.DEFAULT_FROM_EMAIL,
        [msg.correo],
        fail_silently=False,
    )
 
    msg.respondido = True
    msg.save()
 
    return JsonResponse({'status': 'ok'})