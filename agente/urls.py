from django.urls import path
from . import views

app_name = 'agente'

urlpatterns = [
    path('alertas/', views.panel_alertas, name='panel_alertas'),
    path('alertas/<int:pk>/', views.detalle_alerta, name='detalle_alerta'),
    path('alertas/analizar/<int:student_id>/', views.analizar_estudiante_ajax, name='analizar_estudiante'),
    path('alertas/lanzar/', views.lanzar_analisis_completo, name='lanzar_analisis'),
    path('informes/', views.asistente_informe, name='asistente_informe'),
    path('informes/<int:pk>/aceptar/', views.aceptar_informe, name='aceptar_informe'),
    path('configuracion/', views.configuracion_agente, name='configuracion'),
]
