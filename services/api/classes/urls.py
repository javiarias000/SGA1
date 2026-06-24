from django.urls import path, include
from . import views

app_name = 'classes'

urlpatterns = [
    path('enroll_student/', views.enroll_student_view, name='enroll_student_view'),
    path('planificacion/', views.planificacion_view, name='planificacion'),
    path('api/asignar-docente/', views.api_asignar_docente, name='api_asignar_docente'),
    # API DRF
    path('api/v1/', include('classes.api.urls')),
]