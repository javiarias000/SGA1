from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # Autenticación
    path('register/', views.student_register_view, name='register'),
    path('logout/', views.student_logout_view, name='logout'),
    
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