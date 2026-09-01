from django.urls import path
from . import views

urlpatterns = [
    path('panel/',          views.panel_principal, name='panel_principal'),
    path('panel/ingreso-mes/',  views.panel_principal, name='ingreso_mes'),
    path('panel/reservas/',     views.panel_principal, name='panel_reservas'),
    path('panel/ingresos/',     views.panel_principal, name='ingresos'),
    path('panel/resenas/',      views.panel_principal, name='resenas'),
    path('panel/canchas/',      views.panel_principal, name='panel_canchas'),
    path('panel/reservas/<int:id>/aprobar/',  views.aprobar_reserva,       name='aprobar_reserva_admin'),
    path('panel/reservas/<int:id>/eliminar/', views.eliminar_reserva_admin, name='eliminar_reserva_admin'),
    path('panel/reservas/<int:id>/editar/', views.editar_reserva_admin, name='editar_reserva_admin'),
    path('panel/reservas/crear/', views.crear_reserva_admin, name='crear_reserva_admin'),
    path('panel/reservas/horas-ocupadas/', views.horas_ocupadas, name='horas_ocupadas'),
    path('panel/reservas/resumen-mes/', views.resumen_reservas_mes, name='resumen_reservas_mes'),
    path('panel/ingresos/data/', views.ingresos_chart_data, name='ingresos_chart_data'),
    path('panel/mensajes/<int:id>/respondido/', views.marcar_mensaje_respondido, name='marcar_mensaje_respondido'),
    path('panel/reportes/general/', views.generar_reporte_general, name='reporte_general_pdf'),
    path('panel/reportes/mensual/', views.generar_reporte_mes_actual, name='reporte_mensual_pdf'),
    path('mensajes/responder/<int:id>/', views.responder_mensaje, name='responder_mensaje'),
]