from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views.auth import (
    unified_login_view,
    unified_register_view,
    logout_view,
    change_password_view,
)
from .views.home import home_view
from .views.dashboard_views import dashboard, teacher_dashboard_view, student_dashboard_view

app_name = 'users'

urlpatterns = [
    path('login/', unified_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('change-password/', change_password_view, name='change_password'),
    path('dashboard/', dashboard, name='dashboard'),
    path('register/', unified_register_view, name='register'),

    # Password reset views
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            success_url=reverse_lazy('users:password_reset_done')
         ), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), 
         name='password_reset_complete'),
]
