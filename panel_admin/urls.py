from django.urls import path
from . import views

urlpatterns = [
    path('registro_admin/', views.registro_admin, name='registro_admin'),
    path('login_admin/', views.login_admin, name='login_admin'),
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('eliminar/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('panel/', views.panel_principal, name='panel_principal'),
]