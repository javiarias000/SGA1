from rest_framework.routers import DefaultRouter
from .views import ClaseViewSet, EnrollmentViewSet

router = DefaultRouter()
router.register(r'clases', ClaseViewSet)
router.register(r'enrollments', EnrollmentViewSet)

urlpatterns = router.urls