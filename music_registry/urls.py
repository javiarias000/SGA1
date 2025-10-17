from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación y home
    path('', include('users.urls')),

    # Apps principales
    path('classes/', include('classes.urls')),
    path('students/', include('students.urls')),
    path('teachers/', include('teachers.urls')),
]