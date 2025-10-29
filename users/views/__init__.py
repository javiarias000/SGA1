# Importar para que estén disponibles desde users.views
from .auth import unified_login_view, unified_register_view, logout_view
from .redirects import home_redirect_view
from .dashboard_views import dashboard, teacher_dashboard_view, student_dashboard_view
from .decorators import teacher_required, student_required

__all__ = [
    'unified_login_view',
    'unified_register_view', 
    'logout_view',
    'home_redirect_view',
    'dashboard',
    'teacher_dashboard_view',
    'student_dashboard_view',
    'teacher_required',
    'student_required',
]
