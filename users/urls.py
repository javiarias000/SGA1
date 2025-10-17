from django.urls import path
from .views.auth import (
    unified_login_view,
    unified_register_view,
    logout_view,
    
)
from .views.redirects import home_redirect_view
from .views.dashboard_views import dashboard, teacher_dashboard_view, student_dashboard_view


urlpatterns = [
    path('', home_redirect_view, name='home'),
    path('login/', unified_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', unified_register_view, name='register'),
    path('', dashboard, name='dashboard'),
    path('teacher/dashboard/', teacher_dashboard_view, name='teacher_dashboard'),
    path('student/dashboard/', student_dashboard_view, name='student_dashboard'),

]
