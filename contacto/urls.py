from django.urls import path
from . import views

urlpatterns = [
    path('nosotros/', views.nosotros, name='nosotros'),
    path('contacto/', views.nosotros, name='contacto'),  # misma vista

    # Acciones admin para reseñas
    path('resena/<int:id>/archivar/',  views.resena_archivar,  name='resena_archivar'),
    path('resena/<int:id>/restaurar/', views.resena_restaurar, name='resena_restaurar'),
    path('resena/<int:id>/eliminar/',  views.resena_eliminar,  name='resena_eliminar'),
    path('resena/<int:id>/editar/',    views.resena_editar,    name='resena_editar'),
]