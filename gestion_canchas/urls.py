from django.urls import path
from . import views

app_name = 'gestion_canchas'

urlpatterns = [
    # Pública
    path('', views.canchas, name='canchas'),

    # Admin — canchas
    path('admin/',                   views.cancha_admin,    name='cancha_admin'),
    path('admin/agregar/',           views.agregar_cancha,  name='agregar_cancha'),
    path('admin/editar/<int:id>/',   views.editar_cancha,   name='editar_cancha'),
    path('admin/eliminar/<int:id>/', views.eliminar_cancha, name='eliminar_cancha'),
    path('debug/canchas/',           views.debug_canchas,   name='debug_canchas'),

    # Superadmin — sedes ← estas faltaban
    path('sedes/',                       views.lista_sedes,      name='lista_sedes'),
    path('sedes/crear/',                 views.crear_sede,       name='crear_sede'),
    path('sedes/<int:id>/editar/',       views.editar_sede,      name='editar_sede'),
    path('sedes/<int:id>/eliminar/',     views.eliminar_sede,    name='eliminar_sede'),
    path('sedes/<int:id>/toggle/',       views.toggle_sede,      name='toggle_sede'),
    path('sedes/<int:sede_id>/canchas/', views.canchas_por_sede, name='canchas_por_sede'),
]