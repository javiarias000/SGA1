from django.urls import path
from . import views

urlpatterns = [
    # Catálogos
    path('grade-levels/', views.grade_levels, name='informes-grade-levels'),
    path('subjects/', views.subjects_list, name='informes-subjects'),

    # Calificaciones
    path('grades/', views.grades, name='informes-grades'),

    # Docentes
    path('docentes/', views.docentes, name='informes-docentes'),
    path('docentes/upsert/', views.docente_upsert, name='informes-docente-upsert'),

    # Tutores-Cursos
    path('tutores-cursos/', views.tutores_cursos, name='informes-tutores-cursos'),
    path('tutor-por-curso/', views.tutor_por_curso, name='informes-tutor-por-curso'),

    # WhatsApp
    path('wa/instance/', views.wa_instance, name='informes-wa-instance'),
    path('wa/status/<str:instance_name>/', views.wa_status, name='informes-wa-status'),
    path('wa/send/', views.wa_send, name='informes-wa-send'),
    path('wa/send-grades/', views.wa_send_grades, name='informes-wa-send-grades'),
    path('wa/historial/', views.wa_historial, name='informes-wa-historial'),

    # Formularios Google
    path('forms/submit/', views.submit_forms, name='informes-forms-submit'),
    path('submissions/', views.submissions_list, name='informes-submissions'),
    path('submissions/<int:pk>/resend/', views.submission_resend, name='informes-submission-resend'),
    path('submissions/<int:pk>/mark-wa-sent/', views.submission_mark_wa_sent, name='informes-submission-mark-wa-sent'),

    # Sesiones de clase
    path('sesiones/clase/<int:clase_id>/', views.sesiones_clase, name='informes-sesiones'),
    path('sesiones/upsert/', views.sesion_upsert, name='informes-sesion-upsert'),
    path('recomendaciones/upsert/', views.recomendacion_upsert, name='informes-recomendacion-upsert'),
]
