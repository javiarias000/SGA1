from django.urls import path
from students import views

app_name = 'students'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.student_dashboard_view, name='student_dashboard'),
    path('profile/', views.student_profile_view, name='profile'),
    
    # Clases
    path('clases/', views.student_classes_view, name='classes'),
    path('matricula/<int:clase_id>/', views.student_enroll_view, name='enroll'),
    
    # Calificaciones
    path('calificaciones/', views.student_grades_view, name='grades'),
    
    # Asistencia
    path('asistencia/', views.student_attendance_view, name='attendance'),
]