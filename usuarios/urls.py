from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro, name='registro'),
    path('login_admin/', views.login_admin, name='login_admin'),
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('eliminar/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('deshabilitar/<int:id>/', views.deshabilitar_usuario, name='deshabilitar_usuario'),
    path('habilitar/<int:id>/', views.habilitar_usuario, name='habilitar_usuario'),
    path('recuperar_contra/', views.recuperar_contra, name='recuperar_contra'),
    path('verificar_codigo/', views.verificar_codigo, name='verificar_codigo'),
    path('cambiar_contra/', views.cambiar_contra, name='cambiar_contra'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('logout/', views.logout_view, name='logout'),
    path('logout_admin/', views.logout_admin, name='logout_admin'),
]