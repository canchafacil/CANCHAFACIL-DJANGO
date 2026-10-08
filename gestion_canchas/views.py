from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Sede, Cancha
from .forms import CanchaForm


# ==================== VISTAS PÚBLICAS ====================

def canchas(request):
    """
    Vista pública: muestra las canchas disponibles agrupadas por sede.
    """
    sedes = Sede.objects.filter(activa=True).prefetch_related('canchas').order_by('nombre')

    sedes_con_canchas = []
    for sede in sedes:
        canchas_disponibles = sede.canchas.filter(disponible=True).order_by('-creada')
        if canchas_disponibles.exists():
            sedes_con_canchas.append({
                'sede': sede,
                'canchas': canchas_disponibles,
            })

    return render(request, 'gestion_canchas/canchas.html', {
        'sedes_con_canchas': sedes_con_canchas,
    })


# ==================== ADMIN — CRUD CANCHAS ====================

def cancha_admin(request):
    """Muestra el panel de administración de canchas."""
    canchas = Cancha.objects.all().order_by('-creada')
    sedes = Sede.objects.filter(activa=True).order_by('nombre')

    return render(request, 'gestion_canchas/cancha_admin.html', {
        'canchas': canchas,
        'form_agregar': CanchaForm(),
        'sedes': sedes,
    })


def agregar_cancha(request):
    """Agrega una nueva cancha."""
    if request.method == 'POST':
        form = CanchaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:cancha_admin')

        canchas = Cancha.objects.all().order_by('-creada')
        sedes = Sede.objects.filter(activa=True).order_by('nombre')
        return render(request, 'gestion_canchas/cancha_admin.html', {
            'canchas': canchas,
            'form_agregar': form,
            'sedes': sedes,
            'abrir_modal_agregar': True,
        })

    return redirect('gestion_canchas:cancha_admin')


def editar_cancha(request, id):
    """Edita una cancha existente."""
    cancha = get_object_or_404(Cancha, id=id)

    if request.method == 'POST':
        form = CanchaForm(request.POST, request.FILES, instance=cancha)
        if form.is_valid():
            form.save()
            return redirect('gestion_canchas:cancha_admin')
        else:
            print("Errores del formulario editar:", form.errors)
    else:
        form = CanchaForm(instance=cancha)

    return render(request, 'gestion_canchas/editar.html', {
        'form': form,
        'cancha': cancha,
    })


def eliminar_cancha(request, id):
    """Elimina una cancha."""
    get_object_or_404(Cancha, id=id).delete()
    return redirect('gestion_canchas:cancha_admin')


# ==================== SUPERADMIN — SEDES ====================

def lista_sedes(request):
    """Lista todas las sedes."""
    sedes = Sede.objects.prefetch_related('canchas').all()

    return render(
        request,
        'gestion_canchas/sedes/lista_sedes.html',
        {
            'sedes': sedes,
        }
    )


def crear_sede(request):
    """Crea una nueva sede."""
    if request.method == 'POST':
        nombre    = request.POST.get('nombre', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        ciudad    = request.POST.get('ciudad', '').strip()
        telefono  = request.POST.get('telefono', '').strip()

        if nombre and direccion and ciudad:
            Sede.objects.create(
                nombre=nombre,
                direccion=direccion,
                ciudad=ciudad,
                telefono=telefono,
            )
            return redirect('gestion_canchas:lista_sedes')

        sedes = Sede.objects.prefetch_related('canchas').all()
        return render(request, 'gestion_canchas/sedes/lista_sedes.html', {
            'sedes': sedes,
            'abrir_modal': True,
            'error': 'Todos los campos obligatorios deben estar completos.',
        })

    return redirect('gestion_canchas:lista_sedes')


def editar_sede(request, id):
    """Edita una sede existente."""
    sede = get_object_or_404(Sede, id=id)

    if request.method == 'POST':
        sede.nombre = request.POST.get('nombre', '').strip()
        sede.direccion = request.POST.get('direccion', '').strip()
        sede.ciudad = request.POST.get('ciudad', '').strip()
        sede.telefono = request.POST.get('telefono', '').strip()

        sede.save()

        return redirect('gestion_canchas:lista_sedes')

    return render(request, 'gestion_canchas/sedes/editar_sede.html', {
        'sede': sede,
    })


def eliminar_sede(request, id):
    """Elimina una sede."""
    get_object_or_404(Sede, id=id).delete()
    return redirect('gestion_canchas:lista_sedes')


def toggle_sede(request, id):
    """Activa/desactiva una sede."""
    sede = get_object_or_404(Sede, id=id)
    sede.activa = not sede.activa
    sede.save()
    return redirect('gestion_canchas:lista_sedes')


def canchas_por_sede(request, sede_id):
    """Lista las canchas de una sede específica."""
    sede    = get_object_or_404(Sede, id=sede_id)
    canchas = sede.canchas.all().order_by('-creada')
    return render(request, 'gestion_canchas/sedes/canchas_sede.html', {
        'sede': sede,
        'canchas': canchas,
    })


# ==================== DEBUG ====================

def debug_canchas(request):
    """Vista de depuración: devuelve JSON con las canchas."""
    data = list(Cancha.objects.all().values('id', 'nombre', 'disponible', 'sede__nombre'))
    return JsonResponse({'canchas': data}, safe=False)