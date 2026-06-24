from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet, libreta_estudiante_api

router = DefaultRouter()
router.register(r'teachers', TeacherViewSet)

urlpatterns = router.urls + [
    path('libreta/<int:student_id>/', libreta_estudiante_api, name='libreta_api'),
]