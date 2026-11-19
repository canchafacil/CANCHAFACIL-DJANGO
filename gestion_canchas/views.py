
from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Sede, Cancha
from .forms import CanchaForm, SedeForm


# ==================== VISTAS PÚBLICAS ====================

def canchas(request):
    """
    Vista pública: muestra las canchas disponibles agrupadas por sede.
    """

    sedes = Sede.objects.filter(
        activa=True
    ).prefetch_related('canchas').order_by('nombre')

    sedes_con_canchas = []

    for sede in sedes:
        canchas_disponibles = sede.canchas.filter(
            disponible=True
        ).order_by('-creada')

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
    """Edita una cancha desde el panel administrador o superadmin."""

    cancha = get_object_or_404(Cancha, id=id)

    if request.method == 'POST':

        form = CanchaForm(
            request.POST,
            request.FILES,
            instance=cancha
        )

        if form.is_valid():

            cancha = form.save()

            # Identificar desde dónde se está editando
            origen = request.POST.get('origen', '')

            if origen == 'superadmin':
                return redirect(
                    'gestion_canchas:canchas_por_sede',
                    sede_id=cancha.sede_id
                )

            return redirect('gestion_canchas:cancha_admin')

    else:
        form = CanchaForm(instance=cancha)

    return render(request, 'gestion_canchas/editar.html', {
        'form': form,
        'cancha': cancha,
    })



def eliminar_cancha(request, id):
    """Elimina una cancha."""

    cancha = get_object_or_404(Cancha, id=id)
    cancha.delete()

    return redirect('gestion_canchas:cancha_admin')


# ==================== SUPERADMIN — SEDES ====================

def lista_sedes(request):
    """Lista todas las sedes y envía el formulario."""

    sedes = Sede.objects.prefetch_related(
        Prefetch(
            'canchas',
            queryset=Cancha.objects.filter(disponible=True),
            to_attr='canchas_disponibles'
        ),
        'canchas'
    ).all()

    return render(
        request,
        'gestion_canchas/sedes/lista_sedes.html',
        {
            'sedes': sedes,
            'form': SedeForm(),
        }
    )


def crear_sede(request):
    """Crea una nueva sede."""

    if request.method == 'POST':

        form = SedeForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('gestion_canchas:lista_sedes')

        sedes = Sede.objects.prefetch_related(
            Prefetch(
                'canchas',
                queryset=Cancha.objects.filter(disponible=True),
                to_attr='canchas_disponibles'
            ),
            'canchas'
        ).all()

        return render(
            request,
            'gestion_canchas/sedes/lista_sedes.html',
            {
                'sedes': sedes,
                'form': form,
                'abrir_modal': True,
            }
        )

    return redirect('gestion_canchas:lista_sedes')


def editar_sede(request, id):
    """Edita una sede existente."""

    sede = get_object_or_404(Sede, id=id)

    if request.method == 'POST':

        form = SedeForm(request.POST, instance=sede)

        if form.is_valid():

            form.save()

            return redirect('gestion_canchas:lista_sedes')

    else:

        form = SedeForm(instance=sede)

    return render(
        request,
        'gestion_canchas/sedes/editar_sede.html',
        {
            'sede': sede,
            'form': form,
        }
    )


def eliminar_sede(request, id):
    """Elimina una sede."""

    sede = get_object_or_404(Sede, id=id)

    sede.delete()

    return redirect('gestion_canchas:lista_sedes')


def toggle_sede(request, id):
    """Activa o desactiva una sede."""

    sede = get_object_or_404(Sede, id=id)

    sede.activa = not sede.activa

    sede.save()

    return redirect('gestion_canchas:lista_sedes')


def canchas_por_sede(request, sede_id):
    """Lista las canchas de una sede específica."""

    sede = get_object_or_404(Sede, id=sede_id)

    canchas = sede.canchas.all().order_by('-creada')

    return render(
        request,
        'gestion_canchas/sedes/canchas_sede.html',
        {
            'sede': sede,
            'canchas': canchas,
        }
    )

# ==================== DEBUG ====================

def debug_canchas(request):
    """Vista de depuración: solo funciona con DEBUG=True."""

    if not settings.DEBUG:
        raise Http404()

    data = list(
        Cancha.objects.all().values(
            'id',
            'nombre',
            'disponible',
            'sede__nombre'
        )
    )

    return JsonResponse({'canchas': data}, safe=False)
