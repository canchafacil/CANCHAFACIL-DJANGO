from django.shortcuts import render, redirect
from .models import Cancha


def canchas(request):
    todas = Cancha.objects.filter(disponible=True)
    return render(request, 'canchas/canchas.html', {'canchas': todas})


def agregar_cancha(request):
    if request.method == 'POST':
        Cancha.objects.create(
            nombre=request.POST.get('nombre'),
            tipo=request.POST.get('tipo'),
            descripcion=request.POST.get('descripcion', ''),
            precio=request.POST.get('precio'),
            imagen=request.FILES.get('imagen'),
            disponible=request.POST.get('disponible') == 'on',
        )
        return redirect('panel_principal')
    return redirect('panel_principal')


def eliminar_cancha(request, id):
    Cancha.objects.get(id=id).delete()
    return redirect('panel_principal')


def editar_cancha(request, id):
    cancha = Cancha.objects.get(id=id)
    if request.method == 'POST':
        cancha.nombre = request.POST.get('nombre')
        cancha.tipo = request.POST.get('tipo')
        cancha.precio = request.POST.get('precio')
        cancha.disponible = request.POST.get('disponible') == 'on'
        if request.FILES.get('imagen'):
            cancha.imagen = request.FILES.get('imagen')
        cancha.save()
        return redirect('panel_principal')
    return redirect('panel_principal')