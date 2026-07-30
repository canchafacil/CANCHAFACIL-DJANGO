from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import Resena
from usuarios.models import Usuario


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
    return render(request, 'contacto/nosotros.html', {'resenas': resenas, 'promedio': promedio})


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

    resena.jugador   = request.POST.get('jugador', resena.jugador)
    resena.cancha    = request.POST.get('cancha', resena.cancha)
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