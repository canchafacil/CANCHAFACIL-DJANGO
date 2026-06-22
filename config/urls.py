from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('paginas.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('reservas/', include('reservas.urls')),
    path('contacto/', include('contacto.urls')),
    path('canchas/', include('canchas.urls')),
    path('administracion/', include('administracion.urls')),
    path('pagos/', include('pagos.urls')),
]
