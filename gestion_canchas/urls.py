from django.urls import path
from . import views

app_name = 'gestion_canchas'

urlpatterns = [
    # URLs públicas
    path('', views.canchas, name='canchas'),
    
    # URLs de administración (CRUD)
    path('admin/', views.cancha_admin, name='cancha_admin'),
    path('admin/agregar/', views.agregar_cancha, name='agregar_cancha'),
    path('admin/editar/<int:id>/', views.editar_cancha, name='editar_cancha'),
    path('admin/eliminar/<int:id>/', views.eliminar_cancha, name='eliminar_cancha'),
]