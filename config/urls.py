from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static 
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('paginas.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('reservas/', include('reservas.urls')),
    path('contacto/', include('contacto.urls')),
    path('panel_admin/', include('administracion.urls')),
    path('pagos/', include('pagos.urls')),
    path('canchas/', include('gestion_canchas.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)