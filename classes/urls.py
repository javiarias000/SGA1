from django.urls import path
from . import views

urlpatterns = [
    # ============================================
    # AUTENTICACIÓN DOCENTES
    # ============================================
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # ============================================
    # AUTENTICACIÓN ESTUDIANTES
    # ============================================
    path('student/login/', views.student_login_view, name='student_login'),
    path('student/register/', views.student_register_view, name='student_register'),
    
    # ============================================
    # DASHBOARD
    # ============================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('student/dashboard/', views.student_dashboard_view, name='student_dashboard'),
    path('student/classes/', views.student_classes_view, name='student_classes'),
    path('student/grades/', views.student_grades_view, name='student_grades'),
    path('student/attendance/', views.student_attendance_view, name='student_attendance'),
    path('student/profile/', views.student_profile_view, name='student_profile'),
    
    # ============================================
    # ESTUDIANTES (CRUD)
    # ============================================
    path('estudiantes/', views.estudiantes_view, name='estudiantes'),
    path('estudiantes/<int:student_id>/', views.student_detail_view, name='student_detail'),
    path('estudiantes/<int:student_id>/edit/', views.student_edit_view, name='student_edit'),
    path('estudiantes/<int:student_id>/delete/', views.student_delete_view, name='student_delete'),
    path('estudiantes/<int:student_id>/code/', views.student_code_view, name='student_code'),
    # Libreta de calificaciones
    path('estudiantes/<int:student_id>/libreta/', views.report_card_view, name='report_card'),
    
   
    
    # ============================================
    # ACTIVIDADES/CLASES (CRUD)
    # ============================================
    path('registro/', views.registro_view, name='registro'),
    path('actividades/<int:activity_id>/edit/', views.activity_edit_view, name='activity_edit'),
    path('actividades/<int:activity_id>/delete/', views.activity_delete_view, name='activity_delete'),
    
    # ============================================
    # INFORMES
    # ============================================
    path('informes/', views.informes_view, name='informes'),
    path('carpetas/', views.carpetas_view, name='carpetas'),
    
    # ============================================
    # CALIFICACIONES (CRUD)
    # ============================================
    path('calificaciones/', views.grades_view, name='grades'),
    path('calificaciones/<int:grade_id>/edit/', views.grade_edit_view, name='grade_edit'),
    path('calificaciones/<int:grade_id>/delete/', views.grade_delete_view, name='grade_delete'),
    
    # ============================================
    # ASISTENCIA (CRUD)
    # ============================================
    path('asistencia/', views.attendance_view, name='attendance'),
    path('asistencia/<int:attendance_id>/edit/', views.attendance_edit_view, name='attendance_edit'),
    path('asistencia/<int:attendance_id>/delete/', views.attendance_delete_view, name='attendance_delete'),
    
    # ============================================
    # PERFIL
    # ============================================
    path('perfil/', views.profile_view, name='profile'),
    
    # ============================================
    # DESCARGAS
    # ============================================
    path('download/parent/<int:activity_id>/', views.download_parent_report, name='download_parent'),
    path('download/teacher/<int:activity_id>/', views.download_teacher_report, name='download_teacher'),
    
    # ============================================
    # API ENDPOINTS
    # ============================================
    path('api/class-number/', views.get_class_number, name='get_class_number'),
    path('api/student-subjects/', views.get_student_subjects, name='get_student_subjects'),

    # ============================================
    # 3. URLs para envío de emails
    # ============================================

    path('actividades/<int:activity_id>/send-email/', views.send_report_email, name='send_report_email'),
    path('estudiantes/<int:student_id>/send-grades/', views.send_grades_email, name='send_grades_email'),
    path('estudiantes/<int:student_id>/send-attendance/', views.send_attendance_report, name='send_attendance_report'),
    path('estudiantes/<int:student_id>/send-complete/', views.send_complete_report_email, name='send_complete_report'),

    # WhatsApp
    path('actividades/<int:activity_id>/whatsapp/', views.whatsapp_class_report, name='whatsapp_class'),
    path('estudiantes/<int:student_id>/whatsapp-grades/', views.whatsapp_grades_report, name='whatsapp_grades'),
    path('estudiantes/<int:student_id>/whatsapp-attendance/', views.whatsapp_attendance_report, name='whatsapp_attendance'),
]

 