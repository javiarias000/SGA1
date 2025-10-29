from django.urls import path
from .views.auth import (
    unified_login_view,
    unified_register_view,
    logout_view,
    
)
from .views.home import home_view
from .views.dashboard_views import dashboard, teacher_dashboard_view, student_dashboard_view

app_name = 'users'

urlpatterns = [
    path('login/', unified_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('register/', unified_register_view, name='register'),
]
