from django.urls import path
from . import views

urlpatterns = [
    path("", views.reservas, name="reservas"),
    path("crear-reserva/", views.crear_reserva, name="crear_reserva"),
    path("editar/<int:id>/", views.editar_reserva, name="editar_reserva"),
    path("eliminar/<int:id>/", views.eliminar_reserva, name="eliminar_reserva"),
    path("pago/", views.pago, name="pago"),
]