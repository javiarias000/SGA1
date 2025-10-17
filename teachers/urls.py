from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    # Autenticación
    path('register/', views.teacher_register_view, name='register'),
    path('logout/', views.teacher_logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Estudiantes
    path('estudiantes/', views.estudiantes_view, name='estudiantes'),
    path('estudiantes/<int:student_id>/', views.student_detail_view, name='student_detail'),
    path('estudiantes/<int:student_id>/editar/', views.student_edit_view, name='student_edit'),
    path('estudiantes/<int:student_id>/eliminar/', views.student_delete_view, name='student_delete'),
    path('estudiantes/<int:student_id>/codigo/', views.student_code_view, name='student_code'),
    
    # Actividades/Clases
    path('registro/', views.registro_view, name='registro'),
    path('actividades/<int:activity_id>/editar/', views.activity_edit_view, name='activity_edit'),
    path('actividades/<int:activity_id>/eliminar/', views.activity_delete_view, name='activity_delete'),
    
    # Informes
    path('informes/', views.informes_view, name='informes'),
    path('carpetas/', views.carpetas_view, name='carpetas'),
    path('libreta/<int:student_id>/', views.report_card_view, name='report_card'),
    
    # Calificaciones
    path('calificaciones/', views.grades_view, name='grades'),
    path('calificaciones/<int:grade_id>/editar/', views.grade_edit_view, name='grade_edit'),
    path('calificaciones/<int:grade_id>/eliminar/', views.grade_delete_view, name='grade_delete'),
    
    # Asistencia
    path('asistencia/', views.attendance_view, name='attendance'),
    path('asistencia/<int:attendance_id>/editar/', views.attendance_edit_view, name='attendance_edit'),
    path('asistencia/<int:attendance_id>/eliminar/', views.attendance_delete_view, name='attendance_delete'),
    
    # API
    path('api/class-number/', views.get_class_number, name='get_class_number'),
    path('api/student-subjects/', views.get_student_subjects, name='get_student_subjects'),
]