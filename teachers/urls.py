from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [ 
    # Dashboard
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Estudiantes
    path('estudiantes/', views.estudiantes_view, name='estudiantes'),
    path('estudiantes/<int:student_id>/', views.student_detail_view, name='student_detail'),
    path('estudiantes/<int:student_id>/editar/', views.student_edit_view, name='student_edit'),
    path('estudiantes/<int:student_id>/eliminar/', views.student_delete_view, name='student_delete'),
    path('estudiantes/<int:student_id>/codigo/', views.student_code_view, name='student_code'),
    
    # Gestión de tipos de aportes
    path('aportes/', views.gestionar_tipos_aportes, name='gestionar_aportes'),
    
    # Clases teóricas (gestión)
    path('clases/', views.clases_dashboard_view, name='clases_dashboard'),

    # Clases por tipo
    path('teoria/', views.teoria_view, name='teoria_list'),
    path('agrupaciones/', views.agrupaciones_view, name='agrupaciones_list'),
    path('instrumento/', views.instrumento_view, name='instrumento_list'),

    # Actividades/Clases
    path('registro/', views.registro_view, name='registro'),
    path('actividades/<int:activity_id>/editar/', views.activity_edit_view, name='activity_edit'),
    path('actividades/<int:activity_id>/eliminar/', views.activity_delete_view, name='activity_delete'),

    # Calificaciones (CRUD)
    path('calificaciones/<int:grade_id>/editar/', views.grade_edit_view, name='grade_edit'),
    path('calificaciones/<int:grade_id>/eliminar/', views.grade_delete_view, name='grade_delete'),
    
    # Informes
    path('informes/', views.informes_view, name='informes'),
    path('carpetas/', views.carpetas_view, name='carpetas'),
    path('libreta/<int:student_id>/', views.report_card_view, name='report_card'),
    
    # Descargas y comunicación (usadas en templates)
    path('informes/<int:activity_id>/download/parent/', views.download_parent_report, name='download_parent'),
    path('informes/<int:activity_id>/download/teacher/', views.download_teacher_report, name='download_teacher'),
    path('informes/<int:activity_id>/whatsapp/', views.whatsapp_class_report, name='whatsapp_class'),
    path('informes/<int:activity_id>/email/', views.send_report_email, name='send_report_email'),
    path('informes/student/<int:student_id>/email/', views.send_student_report_email, name='send_student_report_email'),
    path('informes/student/<int:student_id>/whatsapp/grades/', views.whatsapp_grades_report, name='whatsapp_grades'),
    path('informes/student/<int:student_id>/whatsapp/attendance/', views.whatsapp_attendance_report, name='whatsapp_attendance'),
    
    # Calificaciones detalladas
    path('calificaciones/detalladas/', views.calificaciones_detalladas_view, name='calificaciones_detalladas'),
    path('api/guardar-calificacion/', views.guardar_calificacion_parcial, name='guardar_calificacion_parcial'),
    
    # API
    path('api/estadisticas/', views.api_estadisticas, name='api_estadisticas'),
    
    # Asistencia
    path('asistencia/', views.attendance_view, name='attendance'),
    path('asistencia/<int:attendance_id>/editar/', views.attendance_edit_view, name='attendance_edit'),
    path('asistencia/<int:attendance_id>/eliminar/', views.attendance_delete_view, name='attendance_delete'),
    
    # API
    path('api/class-number/', views.get_class_number, name='get_class_number'),
    path('api/student-subjects/', views.get_student_subjects, name='get_student_subjects'),
    
    # AJAX endpoints
    path('calificaciones/estudiante/<int:student_id>/', 
         views.obtener_calificaciones_estudiante, 
         name='obtener_calificaciones_estudiante'),
    
    # Libreta del estudiante
    path('libreta/<int:student_id>/', 
         views.ver_libreta_estudiante, 
         name='libreta_estudiante'),

    # Deberes
    path('deberes/', views.lista_deberes_profesor, name='lista_deberes_profesor'),
    path('deberes/crear/', views.crear_deber, name='crear_deber'),
    path('deberes/editar/<int:deber_id>/', views.editar_deber, name='editar_deber'),
    path('deberes/eliminar/<int:deber_id>/', views.eliminar_deber, name='eliminar_deber'),
    path('deberes/entregas/<int:deber_id>/', views.ver_entregas, name='ver_entregas'),
    path('deberes/calificar/<int:entrega_id>/', views.calificar_entrega, name='calificar_entrega'),
]
