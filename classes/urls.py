from django.urls import path
from .views import (

    # Estudiantes
    estudiantes_view,
    student_detail_view,
    student_edit_view,
    student_delete_view,    
    student_code_view,
    
    # Actividades/Clases
    registro_view,
    activity_edit_view,
    activity_delete_view,
    
    # Informes  
    informes_view,
    carpetas_view,
    report_card_view,
    
    # Calificaciones
    grades_view,
    grade_edit_view,
    grade_delete_view,
    
    # Asistencia
    attendance_view,
    attendance_edit_view,
    attendance_delete_view,
    
    # Perfil
    profile_view,
    
    # Vistas Estudiante
    student_classes_view,
    student_grades_view,
    student_attendance_view,
    student_profile_view,
    enroll_in_class_view,
    
    # Descargas
    download_parent_report,
    download_teacher_report,
    
    # API
    get_class_number,
    get_student_subjects,
    
    # Email
    send_report_email,
    send_grades_email,
    send_attendance_report,
    send_complete_report_email,
    
    # WhatsApp
    whatsapp_class_report,
    whatsapp_grades_report,
    whatsapp_attendance_report,
)

app_name = 'teacher' 
app_name = 'student' 

urlpatterns = [
    
    # ============================================
    # DASHBOARD
    # ============================================
    
    path('student/classes/', student_classes_view, name='student_classes'),
    path('student/grades/', student_grades_view, name='student_grades'),
    path('student/attendance/', student_attendance_view, name='student_attendance'),
    path('student/profile/', student_profile_view, name='student_profile'),
    
    # ============================================
    # ESTUDIANTES (CRUD)
    # ============================================
    path('estudiantes/', estudiantes_view, name='estudiantes'),
    path('estudiantes/<int:student_id>/', student_detail_view, name='student_detail'),
    path('estudiantes/<int:student_id>/edit/', student_edit_view, name='student_edit'),
    path('estudiantes/<int:student_id>/delete/', student_delete_view, name='student_delete'),
    path('estudiantes/<int:student_id>/code/', student_code_view, name='student_code'),
    
    # Libreta de calificaciones
    path('estudiantes/<int:student_id>/libreta/', report_card_view, name='report_card'),
    
    # ============================================
    # ACTIVIDADES/CLASES (CRUD)
    # ============================================
    
    path('actividades/<int:activity_id>/edit/', activity_edit_view, name='activity_edit'),
    path('actividades/<int:activity_id>/delete/', activity_delete_view, name='activity_delete'),
    
    # ============================================
    # INFORMES
    # ============================================
    path('informes/', informes_view, name='informes'),
    path('carpetas/', carpetas_view, name='carpetas'),
    
    # ============================================
    # CALIFICACIONES (CRUD)
    # ============================================
    path('calificaciones/', grades_view, name='grades'),
    path('calificaciones/<int:grade_id>/edit/', grade_edit_view, name='grade_edit'),
    path('calificaciones/<int:grade_id>/delete/', grade_delete_view, name='grade_delete'),
    
    # ============================================
    # ASISTENCIA (CRUD)
    # ============================================
    path('asistencia/', attendance_view, name='attendance'),
    path('asistencia/<int:attendance_id>/edit/', attendance_edit_view, name='attendance_edit'),
    path('asistencia/<int:attendance_id>/delete/', attendance_delete_view, name='attendance_delete'),
    
    # ============================================
    # PERFIL
    # ============================================
    path('perfil/', profile_view, name='profile'),
    
    # ============================================
    # DESCARGAS
    # ============================================
    path('download/parent/<int:activity_id>/', download_parent_report, name='download_parent'),
    path('download/teacher/<int:activity_id>/', download_teacher_report, name='download_teacher'),
    
    # ============================================
    # API ENDPOINTS
    # ============================================
    path('api/class-number/', get_class_number, name='get_class_number'),
    path('api/student-subjects/', get_student_subjects, name='get_student_subjects'),

    # ============================================
    # 3. URLs para envío de emails
    # ============================================

    path('actividades/<int:activity_id>/send-email/', send_report_email, name='send_report_email'),
    path('estudiantes/<int:student_id>/send-grades/', send_grades_email, name='send_grades_email'),
    path('estudiantes/<int:student_id>/send-attendance/', send_attendance_report, name='send_attendance_report'),
    path('estudiantes/<int:student_id>/send-complete/', send_complete_report_email, name='send_complete_report'),

    # WhatsApp
    path('actividades/<int:activity_id>/whatsapp/', whatsapp_class_report, name='whatsapp_class'),
    path('estudiantes/<int:student_id>/whatsapp-grades/', whatsapp_grades_report, name='whatsapp_grades'),
    path('estudiantes/<int:student_id>/whatsapp-attendance/', whatsapp_attendance_report, name='whatsapp_attendance'),

    #Matricula
    path('student/classes/<int:clase_id>/enroll/', enroll_in_class_view, name='enroll_in_class'),

]



 