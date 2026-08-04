from django.shortcuts import render, redirect, get_object_or_404
from .models import Cancha
from .forms import CanchaForm

# ==================== VISTAS PÚBLICAS ====================

def canchas(request):
    """Vista pública para mostrar canchas disponibles."""
    todas = Cancha.objects.filter(disponible=True).order_by('-creada')
    return render(request, 
                  'gestion_canchas/canchas.html', 
                  {'canchas': todas})

# ==================== VISTAS DE ADMINISTRACIÓN (CRUD) ====================

def cancha_admin(request):
    """Vista para listar todas las canchas en el panel de administración."""
    canchas = Cancha.objects.all().order_by('-creada')
    return render(request,
                  'gestion_canchas/cancha_admin.html',
                  {'canchas': canchas})

def agregar_cancha(request):
    """Vista para agregar una nueva cancha."""
    if request.method == 'POST':
        form = CanchaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:cancha_admin')
    return redirect('gestion_canchas:cancha_admin')

def editar_cancha(request, id):
    """Vista para editar una cancha existente."""
    cancha = get_object_or_404(Cancha, id=id)
    
    if request.method == 'POST':
        form = CanchaForm(request.POST, request.FILES, instance=cancha)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:cancha_admin')
    
    form = CanchaForm(instance=cancha)
    return render(request,
                  'gestion_canchas/editar.html',
                  {'form': form, 'cancha': cancha})

def eliminar_cancha(request, id):
    """Vista para eliminar una cancha."""
    cancha = get_object_or_404(Cancha, id=id)
    cancha.delete()
    return redirect('gestion_canchas:cancha_admin')