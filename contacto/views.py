from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import Resena
from usuarios.models import Usuario
from reservas.models import Reserva


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
        cancha     = request.POST.get('cancha', '').strip()
        estrellas  = int(request.POST.get('estrellas', 0))
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


def contacto(request):
    return render(request, 'contacto/contacto.html')


@require_POST
def resena_archivar(request, id):
    resena = get_object_or_404(Resena, id=id)
    resena.archivada = True
    resena.save()
    return JsonResponse({'ok': True})


@require_POST
def resena_restaurar(request, id):
    resena = get_object_or_404(Resena, id=id)
    resena.archivada = False
    resena.save()
    return JsonResponse({'ok': True})


@require_POST
def resena_eliminar(request, id):
    resena = get_object_or_404(Resena, id=id)
    resena.delete()
    return JsonResponse({'ok': True})


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


# ---------------------------------------------------------------------
# Vistas para el PERFIL del usuario (editar/eliminar sus propias reseñas)
# ---------------------------------------------------------------------

@require_POST
def editar_resena_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login_admin')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    resena = get_object_or_404(Resena, id=id)

    if resena.correo != usuario.email:
        return redirect('perfil')

    # La cancha ya no se puede cambiar desde acá: queda fija a la reserva
    # original (evita que alguien "mueva" su reseña a otra cancha inventada).
    resena.jugador   = request.POST.get('jugador', resena.jugador)
    resena.estrellas = int(request.POST.get('estrellas', resena.estrellas))
    resena.texto     = request.POST.get('texto', resena.texto).strip()
    resena.save()

    return redirect('perfil')


@require_POST
def eliminar_resena_perfil(request, id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login_admin')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    resena = get_object_or_404(Resena, id=id)

    if resena.correo == usuario.email:
        resena.delete()
        # Nota: al borrar la Resena, el OneToOneField libera la reserva
        # automáticamente (queda con resena=None), así que el usuario
        # podría volver a reseñarla si quiere. Si NO quieres permitir eso,
        # dime y lo bloqueamos por separado.

    return redirect('perfil')