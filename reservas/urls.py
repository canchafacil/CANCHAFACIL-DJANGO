from django.urls import path
from . import views

urlpatterns = [
    path("", views.pagina_reservas, name="reservas"),
    path("formulario/", views.reservas, name="formulario_reservas"),
    path("crear-reserva/", views.crear_reserva, name="crear_reserva"),
    path("editar/<int:id>/", views.editar_reserva, name="editar_reserva"),
    path("eliminar/<int:id>/", views.eliminar_reserva, name="eliminar_reserva"),
    path("pago/", views.pago, name="pago"),
    path("confirmar-pago/", views.confirmar_pago, name="confirmar_pago"),  # NUEVO
    path('perfil/editar/<int:id>/', views.editar_reserva_perfil, name='editar_reserva_perfil'),
    path('perfil/eliminar/<int:id>/', views.eliminar_reserva_perfil, name='eliminar_reserva_perfil'),
]