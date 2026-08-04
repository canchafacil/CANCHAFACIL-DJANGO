from django.urls import path
from . import views

urlpatterns = [
    path('nosotros/', views.nosotros, name='nosotros'),
    path('contacto/', views.contacto, name='contacto'),  # ✅ vista propia

    # Acciones admin para reseñas
    path('resena/<int:id>/archivar/',  views.resena_archivar,  name='resena_archivar'),
    path('resena/<int:id>/restaurar/', views.resena_restaurar, name='resena_restaurar'),
    path('resena/<int:id>/eliminar/',  views.resena_eliminar,  name='resena_eliminar'),
    path('resena/<int:id>/editar/',    views.resena_editar,    name='resena_editar'),
    path('perfil/editar-resena/<int:id>/', views.editar_resena_perfil, name='editar_resena_perfil'),
    path('perfil/eliminar-resena/<int:id>/', views.eliminar_resena_perfil, name='eliminar_resena_perfil'),
]