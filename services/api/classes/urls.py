from django.urls import path, include
from . import views

app_name = 'classes'

urlpatterns = [
    path('enroll_student/', views.enroll_student_view, name='enroll_student_view'),
    path('planificacion/', views.planificacion_view, name='planificacion'),
    path('api/asignar-docente/', views.api_asignar_docente, name='api_asignar_docente'),
    # API DRF
    path('api/v1/', include('classes.api.urls')),

    # Horario
    path('horario/docente/', views.horario_docente_view, name='horario_docente'),
    path('horario/estudiante/', views.horario_estudiante_view, name='horario_estudiante'),

    # Justificaciones
    path('justificacion/<int:asistencia_id>/solicitar/', views.solicitar_justificacion_view, name='solicitar_justificacion'),
    path('justificacion/revisar/', views.revisar_justificaciones_view, name='revisar_justificaciones'),
    path('justificacion/<int:pk>/aprobar/', views.aprobar_justificacion_view, name='aprobar_justificacion'),

    # Recuperaciones
    path('recuperaciones/', views.recuperaciones_view, name='recuperaciones'),
    path('recuperaciones/nueva/', views.registrar_recuperacion_view, name='registrar_recuperacion'),
    path('recuperaciones/<int:pk>/resultado/', views.resultado_recuperacion_view, name='resultado_recuperacion'),
    path('recuperaciones/mis/', views.mis_recuperaciones_view, name='mis_recuperaciones'),
]