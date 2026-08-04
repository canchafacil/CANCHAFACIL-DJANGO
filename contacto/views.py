from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import json
from .models import Resena
from usuarios.models import Usuario
from reservas.models import Reserva


def canchas_reservadas_por(usuario):
    """Devuelve la lista de nombres de cancha únicos donde el usuario
    tiene al menos una reserva Confirmada Y cuya fecha ya pasó
    (se puede reseñar desde el día siguiente a la reserva, no antes)."""
    hoy = timezone.localdate()
    canchas = (
        Reserva.objects
        .filter(correo=usuario.email, estado='Confirmada', fecha__lt=hoy)
        .values_list('cancha', flat=True)
        .distinct()
    )
    return list(canchas)


def nosotros(request):
    if request.method == 'POST':
        usuario_id = request.session.get('usuario_id')

        # Se exige sesión iniciada para publicar reseñas (no solo en el HTML,
        # también acá, por si alguien manda el POST directo sin pasar por el form)
        if not usuario_id:
            return redirect('login')

        usuario = get_object_or_404(Usuario, id=usuario_id)

        jugador   = request.POST.get('jugador', '').strip()
        cancha    = request.POST.get('cancha', '').strip()
        estrellas = int(request.POST.get('estrellas', 0))
        texto     = request.POST.get('texto', '').strip()

        # Validación real: la cancha tiene que estar entre las que el usuario
        # efectivamente reservó, confirmó y cuya fecha ya pasó (mínimo un día).
        # Esto bloquea también intentos de mandar el POST manualmente con una
        # cancha inventada o reseñar antes de haber jugado.
        canchas_validas = canchas_reservadas_por(usuario)
        if cancha not in canchas_validas:
            resenas = Resena.objects.filter(archivada=False).order_by('-fecha')
            total = resenas.count()
            promedio = round(sum(r.estrellas for r in resenas) / total, 1) if total else '—'
            return render(request, 'contacto/nosotros.html', {
                'resenas': resenas,
                'promedio': promedio,
                'canchas_disponibles_resena': canchas_validas,
                'error': 'Solo podés reseñar canchas donde tengas una reserva confirmada y ya jugada (a partir del día siguiente a la reserva).',
            })

        # El nombre y correo se toman de la cuenta logueada, nunca del formulario
        nombre = f"{usuario.first_name} {usuario.last_name}".strip()
        correo = usuario.email

        if texto:
            Resena.objects.create(
                nombre=nombre,
                correo=correo,
                jugador=jugador,
                cancha=cancha,
                estrellas=estrellas,
                texto=texto,
            )
        return redirect('nosotros')

    resenas = Resena.objects.filter(archivada=False).order_by('-fecha')
    total = resenas.count()
    promedio = round(sum(r.estrellas for r in resenas) / total, 1) if total else '—'

    # Canchas que el usuario logueado puede reseñar (lista vacía si no hay sesión)
    canchas_disponibles_resena = []
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        usuario = Usuario.objects.filter(id=usuario_id).first()
        if usuario:
            canchas_disponibles_resena = canchas_reservadas_por(usuario)

    return render(request, 'contacto/nosotros.html', {
        'resenas': resenas,
        'promedio': promedio,
        'canchas_disponibles_resena': canchas_disponibles_resena,
    })


def contacto(request):  # ✅ vista propia para contacto
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
        resena.cancha    = data.get('cancha', resena.cancha)
        resena.estrellas = int(data.get('estrellas', resena.estrellas))
        resena.texto     = data.get('texto', resena.texto).strip()
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

    # Verificación de dueño: solo el autor puede editar su reseña
    if resena.correo != usuario.email:
        return redirect('perfil')

    nueva_cancha = request.POST.get('cancha', resena.cancha)

    # Misma validación: solo puede reasignar la reseña a una cancha
    # que efectivamente reservó, confirmó y cuya fecha ya pasó
    canchas_validas = canchas_reservadas_por(usuario)
    if nueva_cancha not in canchas_validas:
        return redirect('perfil')

    resena.jugador   = request.POST.get('jugador', resena.jugador)
    resena.cancha    = nueva_cancha
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

    # Verificación de dueño: solo el autor puede eliminar su reseña
    if resena.correo == usuario.email:
        resena.delete()

    return redirect('perfil')