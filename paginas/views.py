from django.shortcuts import render
from gestion_canchas.models import Cancha


def inicio(request):
    canchas = Cancha.objects.filter(disponible=True)
    return render(request, 'paginas/index.html', {
        'canchas': canchas,
        'usuario_logueado': bool(request.session.get('usuario_id')),
    })


def nosotros(request):
    return render(request, 'paginas/nosotros.html')