from django.urls import path
from . import views

app_name = 'representante'

urlpatterns = [
    path('', views.rep_dashboard_view, name='dashboard'),
    path('hijo/<int:student_id>/calificaciones/', views.rep_calificaciones_view, name='calificaciones'),
    path('hijo/<int:student_id>/asistencia/', views.rep_asistencia_view, name='asistencia'),
    path('hijo/<int:student_id>/deberes/', views.rep_deberes_view, name='deberes'),
    path('vincular/<int:student_id>/', views.vincular_representante_view, name='vincular'),
]
