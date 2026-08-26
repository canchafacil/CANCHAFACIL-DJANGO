from django.urls import path
from . import views

urlpatterns = [
    path("", views.pagina_reservas, name="reservas"),
    path("formulario/", views.reservas, name="formulario_reservas"),
    path("crear-reserva/", views.crear_reserva, name="crear_reserva"),
    path("editar/<int:id>/", views.editar_reserva, name="editar_reserva"),
    path("pago/", views.pago, name="pago"),
    path("confirmar-pago/", views.confirmar_pago, name="confirmar_pago"),
    path('perfil/editar/<int:id>/', views.editar_reserva_perfil, name='editar_reserva_perfil'),
    path("formulario/<int:cancha_id>/", views.reservas, name="formulario_reservas"),
    path('perfil/cancelar/<int:id>/', views.cancelar_reserva_perfil, name='cancelar_reserva_perfil'),

    # MERCADO PAGO RUTAS
    path("mp/crear/<int:reserva_id>/", views.crear_preferencia_mercadopago, name="crear_preferencia_mercadopago"),
    path("mp/exito/", views.pago_exitoso_mp, name="pago_exitoso_mp"),
    path("mp/cancelado/", views.pago_cancelado_mp, name="pago_cancelado_mp"),
    path("mp/webhook/", views.webhook_mercadopago, name="webhook_mercadopago"),
]