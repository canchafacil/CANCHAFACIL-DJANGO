from functools import wraps
import json

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST, require_GET
from .emails import enviar_correo_html
from .models import Resena, MensajeContacto
from usuarios.models import Usuario
from reservas.models import Reserva


# =====================================================================
# SEGURIDAD (se reutiliza en administracion/views.py)
# =====================================================================

def _es_admin(request):
    """True si hay sesión y el usuario es ADMIN o SUPERADMIN."""
    uid = request.session.get('usuario_id')
    if not uid:
        return False
    u = Usuario.objects.filter(id=uid).first()
    return bool(u) and u.rol in ('ADMIN', 'SUPERADMIN')


def admin_requerido(vista):
    """Para páginas: si no es admin, manda al login."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not _es_admin(request):
            return redirect('login')
        return vista(request, *args, **kwargs)
    return envoltura


def admin_json(vista):
    """Para endpoints AJAX: si no es admin, responde 403 en JSON."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not _es_admin(request):
            return JsonResponse(
                {'ok': False, 'status': 'error', 'error': 'No autorizado'},
                status=403,
            )
        return vista(request, *args, **kwargs)
    return envoltura


# =====================================================================
# RESEÑAS (página pública)
# =====================================================================

def reservas_reseñables_por(usuario):
    """
    Devuelve las reservas del usuario que:
    - Ya están 'completada' (fecha ya pasó, sincronizado automáticamente).
    - Todavía NO tienen una reseña asociada (gracias al OneToOneField).
    Cada reserva completada solo se puede reseñar UNA vez.
    """
    reservas = Reserva.objects.filter(
        correo=usuario.email,
        estado=Reserva.ESTADO_COMPLETADA,
    )
    # Sincroniza por si alguna todavía no se marcó como completada
    for r in reservas:
        r.sincronizar_estado()

    # Solo las que no tienen reseña todavía (related_name='resena' del OneToOneField)
    return [r for r in reservas if not hasattr(r, 'resena') or r.resena is None]


def nosotros(request):
    if request.method == 'POST':
        usuario_id = request.session.get('usuario_id')

        if not usuario_id:
            return redirect('login')

        usuario = get_object_or_404(Usuario, id=usuario_id)

        reserva_id = request.POST.get('reserva_id', '').strip()
        jugador    = request.POST.get('jugador', '').strip()
        try:
            estrellas = int(request.POST.get('estrellas', 0))
        except (TypeError, ValueError):
            estrellas = 0
        texto      = request.POST.get('texto', '').strip()

        # Validación real: la reserva tiene que ser del usuario, estar
        # completada, y no tener ya una reseña asociada.
        reservas_validas = reservas_reseñables_por(usuario)
        reserva = next((r for r in reservas_validas if str(r.id) == reserva_id), None)

        if reserva is None:
            resenas = Resena.objects.filter(archivada=False).order_by('-fecha')
            total = resenas.count()
            promedio = round(sum(r.estrellas for r in resenas) / total, 1) if total else '—'
            return render(request, 'contacto/nosotros.html', {
                'resenas': resenas,
                'promedio': promedio,
                'reservas_reseñables': reservas_validas,
                'error': 'Solo podés reseñar una reserva propia que ya esté completada y que no hayas reseñado todavía.',
            })

        nombre = f"{usuario.first_name} {usuario.last_name}".strip()
        correo = usuario.email

        if texto:
            Resena.objects.create(
                nombre=nombre,
                correo=correo,
                jugador=jugador,
                cancha=reserva.cancha,  # se toma de la reserva real, no del form
                estrellas=estrellas,
                texto=texto,
                reserva=reserva,
            )
        return redirect('nosotros')

    resenas = Resena.objects.filter(archivada=False).order_by('-fecha')
    total = resenas.count()
    promedio = round(sum(r.estrellas for r in resenas) / total, 1) if total else '—'

    reservas_reseñables = []
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        usuario = Usuario.objects.filter(id=usuario_id).first()
        if usuario:
            reservas_reseñables = reservas_reseñables_por(usuario)

    return render(request, 'contacto/nosotros.html', {
        'resenas': resenas,
        'promedio': promedio,
        'reservas_reseñables': reservas_reseñables,
    })


# =====================================================================
# CONTÁCTANOS (formulario público, AJAX)
# =====================================================================

def contacto(request):
    if request.method == 'POST':
        nombre   = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        correo   = request.POST.get('correo', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        asunto   = request.POST.get('asunto', '').strip()
        mensaje  = request.POST.get('mensaje', '').strip()

        if not (nombre and correo and asunto and mensaje):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Completa nombre, correo, asunto y mensaje.',
            }, status=400)

        m = MensajeContacto.objects.create(
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            telefono=telefono,
            asunto=asunto,
            mensaje=mensaje,
        )

        ok, error = enviar_correo_html(
            'Hemos recibido tu mensaje - CanchaFácil',
            correo,
            'emails/confirmacion_contacto.html',
            {
                'nombre': nombre,
                'asunto': asunto,
                'mensaje': mensaje,
                'fecha': timezone.localtime(m.fecha).strftime('%d/%m/%Y'),
            },
        )

        if not ok:
            # El mensaje ya se guardó en la BD aunque el correo falle
            return JsonResponse({
                'status': 'ok',
                'correo_enviado': False,
                'mensaje': 'Tu mensaje se guardó, pero no pudimos enviarte el correo de confirmación.',
            })

        return JsonResponse({'status': 'ok', 'correo_enviado': True})

    return render(request, 'contacto/contacto.html')


# =====================================================================
# RESEÑAS (panel admin)
# =====================================================================

@admin_json
@require_POST
def resena_archivar(request, id):
    resena = get_object_or_404(Resena, id=id)
    resena.archivada = True
    resena.save()
    return JsonResponse({'ok': True})


@admin_json
@require_POST
def resena_restaurar(request, id):
    resena = get_object_or_404(Resena, id=id)
    resena.archivada = False
    resena.save()
    return JsonResponse({'ok': True})


@admin_json
@require_POST
def resena_eliminar(request, id):
    resena = get_object_or_404(Resena, id=id)
    resena.delete()
    return JsonResponse({'ok': True})


@admin_json
@require_POST
def resena_editar(request, id):
    resena = get_object_or_404(Resena, id=id)
    try:
        data = json.loads(request.body)
        resena.nombre    = data.get('nombre', resena.nombre).strip()
        resena.jugador   = data.get('jugador', resena.jugador)
        resena.estrellas = int(data.get('estrellas', resena.estrellas))
        resena.texto     = data.get('texto', resena.texto).strip()
        # 'cancha' ya NO se deja editar manualmente: viene fija de la reserva
        resena.save()
        return JsonResponse({
            'ok': True,
            'nombre': resena.nombre,
            'jugador': resena.jugador,
            'cancha': resena.cancha,
            'estrellas': resena.estrellas,
            'texto': resena.texto,
        })
    except Exception:
        return JsonResponse({'ok': False}, status=400)


# =====================================================================
# RESEÑAS (perfil del usuario)
# =====================================================================

@require_POST
def editar_resena_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    resena = get_object_or_404(Resena, id=id)

    if resena.correo != usuario.email:
        return redirect('perfil')

    # La cancha no se puede cambiar: queda fija a la reserva original.
    resena.jugador = request.POST.get('jugador', resena.jugador)
    try:
        resena.estrellas = int(request.POST.get('estrellas', resena.estrellas))
    except (TypeError, ValueError):
        pass
    resena.texto = request.POST.get('texto', resena.texto).strip()
    resena.save()

    return redirect('perfil')


@require_POST
def eliminar_resena_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    resena = get_object_or_404(Resena, id=id)

    if resena.correo == usuario.email:
        resena.delete()
        # Al borrar la Resena, el OneToOneField libera la reserva
        # (queda con resena=None) y el usuario podría reseñarla otra vez.

    return redirect('perfil')


# =====================================================================
# MENSAJES DE CONTACTO (panel admin)
# =====================================================================

def _serializar_mensaje(m):
    return {
        'id': m.id,
        'nombre': f'{m.nombre} {m.apellido}'.strip(),
        'correo': m.correo,
        'telefono': m.telefono,
        'asunto': m.asunto,
        'mensaje': m.mensaje,
        'fecha': timezone.localtime(m.fecha).strftime('%d/%m/%Y %H:%M'),
        'leido': m.leido,
        'respondido': m.respondido,
        'respuesta': m.respuesta,
        'fecha_respuesta': (
            timezone.localtime(m.fecha_respuesta).strftime('%d/%m/%Y %H:%M')
            if m.fecha_respuesta else ''
        ),
    }


def enviar_respuesta_contacto(m, respuesta):
    """
    Envía la respuesta con el diseño de CanchaFácil y, si sale bien,
    guarda la respuesta y marca el mensaje como leído y respondido.
    Devuelve (ok, error).
    """
    ok, error = enviar_correo_html(
        f'Re: {m.asunto} - CanchaFácil',
        m.correo,
        'emails/respuesta_contacto.html',
        {
            'nombre': m.nombre,
            'asunto': m.asunto,
            'mensaje_original': m.mensaje,
            'respuesta': respuesta,
            'fecha': timezone.localtime(m.fecha).strftime('%d/%m/%Y'),
        },
    )
    if not ok:
        return False, f'No se pudo enviar el correo: {error}'

    ahora = timezone.now()
    m.respuesta = respuesta
    m.respondido = True
    m.fecha_respuesta = ahora
    if not m.leido:
        m.leido = True
        m.fecha_lectura = ahora
    m.save()
    return True, ''


@admin_json
@require_GET
def mensajes_data(request):
    pendientes = MensajeContacto.objects.filter(
        leido=False, respondido=False
    ).order_by('-fecha')

    historial = MensajeContacto.objects.filter(
        Q(leido=True) | Q(respondido=True)
    ).order_by('-fecha')

    return JsonResponse({
        'ok': True,
        'pendientes': [_serializar_mensaje(m) for m in pendientes],
        'historial': [_serializar_mensaje(m) for m in historial],
    })


@admin_json
@require_POST
def mensaje_marcar_leido(request, id):
    m = get_object_or_404(MensajeContacto, id=id)
    if not m.leido:
        m.leido = True
        m.fecha_lectura = timezone.now()
        m.save()
    return JsonResponse({'ok': True})


@admin_json
@require_POST
def mensaje_responder(request, id):
    m = get_object_or_404(MensajeContacto, id=id)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    respuesta = (data.get('respuesta') or '').strip()
    if not respuesta:
        return JsonResponse({'ok': False, 'error': 'Escribe una respuesta.'}, status=400)

    ok, error = enviar_respuesta_contacto(m, respuesta)
    if not ok:
        return JsonResponse({'ok': False, 'error': error}, status=500)

    return JsonResponse({'ok': True})