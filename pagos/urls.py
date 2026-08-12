# pagos/urls.py
from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('factura/<int:reserva_id>/', views.descargar_factura, name='descargar_factura'),
]