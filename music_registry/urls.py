from django.contrib import admin
from django.urls import path, include
from users.views.home import home_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
     # Vista principal (landing pública)
    path('', home_view, name='home'),
    
    # Autenticación y home (namespaced)
    path('users/', include(("users.urls", "users"), namespace='users')),

    # Apps principales (namespaced)
    path('students/', include(("students.urls", "students"), namespace='students')),
    path('teachers/', include(("teachers.urls", "teachers"), namespace='teachers')),
] + (static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) if settings.DEBUG else [])
