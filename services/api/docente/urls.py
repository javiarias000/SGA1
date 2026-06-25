from django.urls import path
from . import views

app_name = 'docente'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('estudiantes/', views.mis_estudiantes, name='estudiantes'),
    path('clase/<int:pk>/', views.clase_detail, name='clase_detail'),
    path('clase/<int:pk>/calificaciones/', views.calificaciones, name='calificaciones'),
    path('clase/<int:pk>/asistencia/', views.asistencia, name='asistencia'),
]
