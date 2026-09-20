from django.urls import path
from . import views

app_name = 'comunidad'

urlpatterns = [
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),

    path('partidos/', views.listar_partidos, name='listar_partidos'),
    path('partidos/crear/', views.crear_partido, name='crear_partido'),
    path('partidos/<int:partido_id>/unirse/', views.unirse_partido, name='unirse_partido'),

    path('retos/', views.listar_retos, name='listar_retos'),
    path('retos/crear/', views.crear_reto, name='crear_reto'),
    path('retos/<int:reto_id>/aceptar/', views.aceptar_reto, name='aceptar_reto'),

    path('muro/', views.listar_muro, name='listar_muro'),
    path('muro/crear/', views.crear_muro, name='crear_muro'),
]