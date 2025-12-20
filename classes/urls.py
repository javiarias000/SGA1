from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    path('enroll_student/', views.enroll_student_view, name='enroll_student_view'),
]