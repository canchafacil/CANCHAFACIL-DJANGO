from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Resena


def nosotros(request):
    """Página pública con formulario de reseña."""
    if request.method == 'POST':
        nombre    = request.POST.get('nombre', '').strip()
        jugador   = request.POST.get('jugador', '').strip()
        cancha    = request.POST.get('cancha', '').strip()
        estrellas = int(request.POST.get('estrellas', 0))
        texto     = request.POST.get('texto', '').strip()

        if nombre and texto:
            Resena.objects.create(
                nombre=nombre,
                jugador=jugador,
                cancha=cancha,
                estrellas=estrellas,
                texto=texto,
            )
        return redirect('nosotros')

    resenas = Resena.objects.filter(archivada=False).order_by('-fecha')
    return render(request, 'contacto/nosotros.html', {'resenas': resenas})


# ── Acciones del panel admin ──

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
        resena.texto = data.get('texto', resena.texto)
        resena.save()
        return JsonResponse({'ok': True})
    except Exception:
        return JsonResponse({'ok': False}, status=400)