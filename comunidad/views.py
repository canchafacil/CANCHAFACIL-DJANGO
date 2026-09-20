"""
Vistas de partidos abiertos, retos y muro de comunidad.

Reglas:
  1. Solo se publica con una reserva TUYA (correo == tu email), CONFIRMADA, pagada por
     completo (saldo_pendiente <= 0), futura y sin otra publicación.
  2. Lo que se lista sale de esa reserva: si la reserva se edita o se cancela,
     el partido/reto la sigue (día y hora se calculan al listar) o desaparece.
  3. Cada publicación define si quien entra debe pagar (cobra) y cuánto (valor).
  4. Si cobra, para apuntarse/aceptar hay que confirmar el pago (acepta_pago=1) y se crea un Aporte.
"""
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from gestion_canchas.models import Cancha
from reservas.models import Reserva          # AJUSTA si tu app se llama distinto
from usuarios.models import Usuario

from .models import PartidoAbierto, Reto, Aporte, PublicacionMuro

VALOR_MIN, VALOR_MAX = 1000, 500000
RELACION = {'partido': 'partido_abierto', 'reto': 'reto'}   # related_name en Reserva


# ======================= AYUDAS =======================
def _usuario(request):
    uid = request.session.get('usuario_id')
    return Usuario.objects.filter(id=uid).first() if uid else None


def _no_sesion():
    return JsonResponse({'error': 'Debes iniciar sesión para continuar'}, status=401)


def _err(mensaje, status=400):
    return JsonResponse({'error': mensaje}, status=status)


def _pesos(n):
    return '$' + f'{int(n):,}'.replace(',', '.')


def _hora12(h, m):
    return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def _rango(reserva):
    """('6:00 PM', '8:00 PM') a partir de las horas reservadas (la última dura 1 hora)."""
    horas = sorted(reserva.get_horas())
    h1, m1 = map(int, horas[0].split(':'))
    h2, m2 = map(int, horas[-1].split(':'))
    return _hora12(h1, m1), _hora12((h2 + 1) % 24, m2)


def _reservas_publicables(usuario, tipo):
    """Reservas del usuario que ya pueden respaldar un partido/reto."""
    qs = Reserva.objects.filter(
        correo__iexact=usuario.email,
        estado=Reserva.ESTADO_CONFIRMADA,
        saldo_pendiente__lte=0,      # pagada por completo (si quieres permitir abono, quita esta línea)
        monto_pagado__gt=0,
        fecha__gte=timezone.localdate(),
        **{f'{RELACION[tipo]}__isnull': True},
    ).order_by('fecha', 'hora')
    return [r for r in qs if not r.ya_paso()]


def _leer_cobro(request):
    """(cobra, valor, error)"""
    if request.POST.get('cobra') != '1':
        return False, 0, None
    try:
        valor = int(request.POST.get('valor', ''))
    except ValueError:
        return False, 0, 'Ingresa el valor que se debe pagar'
    if not VALOR_MIN <= valor <= VALOR_MAX:
        return False, 0, f'El valor debe estar entre {_pesos(VALOR_MIN)} y {_pesos(VALOR_MAX)}'
    return True, valor, None


def _reserva_para_publicar(request, usuario, tipo):
    """(reserva, cancha, error)"""
    try:
        rid = int(request.POST.get('reserva_id', ''))
    except ValueError:
        return None, None, 'Elige el día y la hora de una de tus reservas pagadas'
    reserva = next((r for r in _reservas_publicables(usuario, tipo) if r.id == rid), None)
    if not reserva:
        return None, None, 'Solo puedes publicar con una reserva tuya, pagada por completo y que aún no haya pasado'
    cancha = Cancha.objects.filter(nombre=reserva.cancha).select_related('sede').first()
    if not cancha:
        return None, None, 'La cancha de esta reserva ya no existe'
    return reserva, cancha, None


def _crear_pago(request, aporte):
    """
    Punto de conexión con Mercado Pago. Debe crear la preferencia de pago del aporte,
    guardar aporte.mp_preference_id y devolver la URL de pago (o None si aún no está conectado).
    Cuando el pago se confirme (webhook), marca aporte.pagado = True.
    """
    return None


def _respuesta_aporte(request, aporte, texto_sin_pago):
    pago_url = _crear_pago(request, aporte)
    if pago_url:
        return {'ok': True, 'pago_url': pago_url}
    return {'ok': True, 'mensaje': f'{texto_sin_pago} Tu aporte de {_pesos(aporte.monto)} queda pendiente de pago.'}


# ======================= CALENDARIO =======================
@require_GET
def mis_reservas(request):
    """Alimenta el calendario: reservas pagadas, futuras y sin publicar para ese tipo."""
    usuario = _usuario(request)
    if not usuario:
        return _no_sesion()
    tipo = request.GET.get('tipo', 'partido')
    if tipo not in RELACION:
        return _err('Tipo inválido')
    canchas = {c.nombre: c for c in Cancha.objects.select_related('sede')}
    data = []
    for r in _reservas_publicables(usuario, tipo):
        ini, fin = _rango(r)
        cancha = canchas.get(r.cancha)
        data.append({
            'id': r.id,
            'fecha': r.fecha.isoformat(),           # YYYY-MM-DD
            'hora_inicio': ini,
            'hora_fin': fin,
            'cancha': r.cancha,
            'sede': cancha.sede.nombre if cancha else '',
            'precio': int(r.precio_total or r.calcular_total()),
        })
    return JsonResponse({'reservas': data})


# ======================= PARTIDOS =======================
@require_GET
def listar_partidos(request):
    usuario = _usuario(request)
    unidos = set(usuario.partidos_unidos.values_list('id', flat=True)) if usuario else set()
    qs = (PartidoAbierto.objects
          .filter(reserva__isnull=False,
                  reserva__estado=Reserva.ESTADO_CONFIRMADA,
                  reserva__saldo_pendiente__lte=0,
                  reserva__fecha__gte=timezone.localdate())
          .select_related('reserva', 'cancha__sede')
          .order_by('reserva__fecha', '-creado'))
    data = []
    for p in qs:
        if p.reserva.ya_paso():
            continue
        ini, fin = _rango(p.reserva)
        data.append({
            'id': p.id,
            'sede': f'{p.cancha.nombre} — {p.cancha.sede.nombre}',
            'fecha': p.reserva.fecha.strftime('%d/%m/%Y'),
            'horario': f'{ini} – {fin}',
            'faltan': p.jugadores_faltan,
            'ya_unido': usuario is not None and (p.creador_id == usuario.id or p.id in unidos),
            'cobra': p.cobra,
            'valor': p.valor,
        })
    return JsonResponse({'partidos': data})


@require_POST
def crear_partido(request):
    usuario = _usuario(request)
    if not usuario:
        return _no_sesion()
    reserva, cancha, error = _reserva_para_publicar(request, usuario, 'partido')
    if error:
        return _err(error)
    try:
        faltan = int(request.POST.get('faltan', ''))
    except ValueError:
        return _err('Indica cuántos jugadores faltan')
    if not 1 <= faltan <= 21:
        return _err('Deben faltar entre 1 y 21 jugadores')
    cobra, valor, error = _leer_cobro(request)
    if error:
        return _err(error)
    ini, fin = _rango(reserva)
    try:
        PartidoAbierto.objects.create(
            reserva=reserva, cancha=cancha, fecha=reserva.fecha, hora_texto=f'{ini} – {fin}',
            jugadores_faltan=faltan, creador=usuario, cobra=cobra, valor=valor,
        )
    except IntegrityError:   # doble clic: la reserva ya se publicó
        return _err('Esa reserva ya tiene una publicación')
    return JsonResponse({'ok': True})


@require_POST
def unirse_partido(request, partido_id):
    usuario = _usuario(request)
    if not usuario:
        return _no_sesion()
    with transaction.atomic():
        try:
            # Sin select_related: en PostgreSQL no se puede bloquear un join con FK nula
            p = PartidoAbierto.objects.select_for_update().get(pk=partido_id)
        except PartidoAbierto.DoesNotExist:
            return _err('Este partido ya no está disponible', 404)
        r = p.reserva
        if not r or r.estado != Reserva.ESTADO_CONFIRMADA or r.ya_paso():
            return _err('Este partido ya no está disponible', 404)
        if p.creador_id == usuario.id:
            return _err('Tú publicaste este partido')
        if p.participantes.filter(pk=usuario.pk).exists():
            return _err('Ya estás dentro de este partido')
        if p.jugadores_faltan <= 0:
            return _err('El equipo ya está completo')
        if p.cobra and request.POST.get('acepta_pago') != '1':
            return _err(f'Este partido tiene un aporte de {_pesos(p.valor)}. Confirma el pago para apuntarte.')

        p.participantes.add(usuario)
        p.jugadores_faltan -= 1
        p.save(update_fields=['jugadores_faltan'])
        aporte = Aporte.objects.create(usuario=usuario, partido=p, monto=p.valor) if p.cobra else None

    if aporte:
        return JsonResponse(_respuesta_aporte(request, aporte, 'Te apuntaste al partido.'))
    return JsonResponse({'ok': True, 'mensaje': '¡Te uniste al partido! No debes pagar nada.'})


# ======================= RETOS =======================
@require_GET
def listar_retos(request):
    qs = (Reto.objects
          .filter(reserva__isnull=False,
                  reserva__estado=Reserva.ESTADO_CONFIRMADA,
                  reserva__saldo_pendiente__lte=0,
                  reserva__fecha__gte=timezone.localdate())
          .select_related('reserva', 'cancha__sede')
          .order_by('reserva__fecha', '-creado'))
    data = []
    for t in qs:
        if t.reserva.ya_paso():
            continue
        ini, fin = _rango(t.reserva)
        data.append({
            'id': t.id,
            'equipo': t.equipo,
            'sede': f'{t.cancha.nombre} — {t.cancha.sede.nombre}',
            'horario': f'{t.reserva.fecha.strftime("%d/%m/%Y")} {ini} – {fin}',
            'aceptado': t.aceptado,
            'cobra': t.cobra,
            'valor': t.valor,
        })
    return JsonResponse({'retos': data})


@require_POST
def crear_reto(request):
    usuario = _usuario(request)
    if not usuario:
        return _no_sesion()
    reserva, cancha, error = _reserva_para_publicar(request, usuario, 'reto')
    if error:
        return _err(error)
    equipo = request.POST.get('equipo', '').strip()[:100]
    if not equipo:
        return _err('Escribe el nombre de tu equipo')
    cobra, valor, error = _leer_cobro(request)
    if error:
        return _err(error)
    ini, fin = _rango(reserva)
    try:
        Reto.objects.create(
            reserva=reserva, cancha=cancha, equipo=equipo,
            horario=f'{reserva.fecha.strftime("%d/%m/%Y")} {ini} – {fin}',
            creador=usuario, cobra=cobra, valor=valor,
        )
    except IntegrityError:
        return _err('Esa reserva ya tiene una publicación')
    return JsonResponse({'ok': True})


@require_POST
def aceptar_reto(request, reto_id):
    usuario = _usuario(request)
    if not usuario:
        return _no_sesion()
    with transaction.atomic():
        try:
            t = Reto.objects.select_for_update().get(pk=reto_id)
        except Reto.DoesNotExist:
            return _err('Este reto ya no está disponible', 404)
        r = t.reserva
        if not r or r.estado != Reserva.ESTADO_CONFIRMADA or r.ya_paso():
            return _err('Este reto ya no está disponible', 404)
        if t.creador_id == usuario.id:
            return _err('No puedes aceptar tu propio reto')
        if t.aceptado:
            return _err('Este reto ya fue aceptado')
        if t.cobra and request.POST.get('acepta_pago') != '1':
            return _err(f'Este reto tiene un aporte de {_pesos(t.valor)}. Confirma el pago para aceptarlo.')

        t.aceptado = True
        t.aceptado_por = usuario
        t.save(update_fields=['aceptado', 'aceptado_por'])
        aporte = Aporte.objects.create(usuario=usuario, reto=t, monto=t.valor) if t.cobra else None

    ini, fin = _rango(r)
    respuesta = {
        'ok': True,
        'equipo': t.equipo,
        'sede': f'{t.cancha.nombre} — {t.cancha.sede.nombre}',
        'horario': f'{r.fecha.strftime("%d/%m/%Y")} {ini} – {fin}',
        'mensaje': '¡Reto aceptado! No debes pagar nada.',
    }
    if aporte:
        respuesta.update(_respuesta_aporte(request, aporte, '¡Reto aceptado!'))
    return JsonResponse(respuesta)


# ======================= MURO =======================
@require_GET
def listar_muro(request):
    publicaciones = PublicacionMuro.objects.select_related('usuario').order_by('-creado')[:100]
    data = [{
        'id': pub.id,
        'nombre_mostrar': pub.nombre_mostrar,
        'texto': pub.texto,
        'creado': pub.creado.strftime('%d/%m/%Y %H:%M'),
    } for pub in publicaciones]
    return JsonResponse({'publicaciones': data})


@require_POST
def crear_muro(request):
    usuario = _usuario(request)
    if not usuario:
        return _no_sesion()
    texto = request.POST.get('texto', '').strip()
    if not texto:
        return _err('Escribe algo para publicar')
    if len(texto) > 500:
        return _err('El texto no puede superar los 500 caracteres')
    nombre_mostrar = request.POST.get('nombre_mostrar', '').strip()[:100] or usuario.get_full_name() or usuario.email
    PublicacionMuro.objects.create(usuario=usuario, nombre_mostrar=nombre_mostrar, texto=texto)
    return JsonResponse({'ok': True})