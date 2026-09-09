from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Cancha
from .forms import CanchaForm


# ── Helpers de rol ────────────────────────────────────────────────────────────
def es_admin(request):
    return request.session.get('admin_rol') in ('ADMIN', 'SUPERADMIN')

def es_superadmin(request):
    return request.session.get('admin_rol') == 'SUPERADMIN'


# ==================== VISTAS PÚBLICAS ====================

def canchas(request):
    todas = Cancha.objects.filter(disponible=True).order_by('-creada')
    return render(request, 'gestion_canchas/canchas.html', {'canchas': todas})


# ==================== ADMIN — CRUD CANCHAS ====================

def cancha_admin(request):
    if not es_admin(request):
        return redirect('login_admin')
    canchas = Cancha.objects.all().order_by('-creada')
    return render(request, 'gestion_canchas/cancha_admin.html', {
        'canchas': canchas,
        'form_agregar': CanchaForm()
    })

def agregar_cancha(request):
    if not es_admin(request):
        return redirect('login_admin')
    if request.method == 'POST':
        form = CanchaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:cancha_admin')
        canchas = Cancha.objects.all().order_by('-creada')
        return render(request, 'gestion_canchas/cancha_admin.html', {
            'canchas': canchas,
            'form_agregar': form,
            'abrir_modal_agregar': True,
        })
    return redirect('gestion_canchas:cancha_admin')

def editar_cancha(request, id):
    if not es_admin(request):
        return redirect('login_admin')
    cancha = get_object_or_404(Cancha, id=id)
    if request.method == 'POST':
        form = CanchaForm(request.POST, request.FILES, instance=cancha)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:cancha_admin')
    else:
        form = CanchaForm(instance=cancha)
    return render(request, 'gestion_canchas/editar.html', {
        'form': form, 'cancha': cancha
    })

def eliminar_cancha(request, id):
    if not es_admin(request):
        return redirect('login_admin')
    get_object_or_404(Cancha, id=id).delete()
    return redirect('gestion_canchas:cancha_admin')


# ==================== SUPERADMIN — SEDES ====================

def lista_sedes(request):
    if not es_superadmin(request):
        return redirect('login_admin')
    sedes = Sede.objects.prefetch_related('canchas').all()
    return render(request, 'gestion_canchas/sedes/lista_sedes.html', {
        'sedes': sedes,
        'form':  SedeForm(),
    })

def crear_sede(request):
    if not es_superadmin(request):
        return redirect('login_admin')
    if request.method == 'POST':
        form = SedeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:lista_sedes')
        return render(request, 'gestion_canchas/sedes/lista_sedes.html', {
            'sedes':       Sede.objects.prefetch_related('canchas').all(),
            'form':        form,
            'abrir_modal': True,
        })
    return redirect('gestion_canchas:lista_sedes')

def editar_sede(request, id):
    if not es_superadmin(request):
        return redirect('login_admin')
    sede = get_object_or_404(Sede, id=id)
    if request.method == 'POST':
        form = SedeForm(request.POST, instance=sede)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:lista_sedes')
    else:
        form = SedeForm(instance=sede)
    return render(request, 'gestion_canchas/sedes/editar_sede.html', {
        'form': form, 'sede': sede
    })

def eliminar_sede(request, id):
    if not es_superadmin(request):
        return redirect('login_admin')
    get_object_or_404(Sede, id=id).delete()
    return redirect('gestion_canchas:lista_sedes')

def toggle_sede(request, id):
    if not es_superadmin(request):
        return redirect('login_admin')
    sede = get_object_or_404(Sede, id=id)
    sede.activa = not sede.activa
    sede.save()
    return redirect('gestion_canchas:lista_sedes')

def canchas_por_sede(request, sede_id):
    if not es_superadmin(request):
        return redirect('login_admin')
    sede    = get_object_or_404(Sede, id=sede_id)
    canchas = sede.canchas.all().order_by('-creada')
    return render(request, 'gestion_canchas/sedes/canchas_sede.html', {
        'sede': sede, 'canchas': canchas
    })


# ==================== DEBUG ====================

def debug_canchas(request):
    data = list(Cancha.objects.all().values('id', 'nombre', 'disponible', 'sede__nombre'))
    return JsonResponse({'canchas': data}, safe=False)