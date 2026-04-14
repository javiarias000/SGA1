from django.urls import path, include
from . import views

app_name = 'classes'

urlpatterns = [
    path('enroll_student/', views.enroll_student_view, name='enroll_student_view'),
    # API DRF
    path('api/v1/', include('classes.api.urls')),
]