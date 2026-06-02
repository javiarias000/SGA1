from rest_framework.routers import DefaultRouter
from .views import (
    ClaseViewSet, EnrollmentViewSet, TipoAporteViewSet,
    CalificacionParcialViewSet, AsistenciaViewSet,
    ActivityViewSet, DeberViewSet, DeberEntregaViewSet,
)

router = DefaultRouter()
router.register(r'clases', ClaseViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'tipos-aportes', TipoAporteViewSet)
router.register(r'calificaciones', CalificacionParcialViewSet, basename='calificaciones')
router.register(r'asistencia', AsistenciaViewSet, basename='asistencia')
router.register(r'actividades', ActivityViewSet, basename='actividades')
router.register(r'deberes', DeberViewSet, basename='deberes')
router.register(r'entregas', DeberEntregaViewSet, basename='entregas')

urlpatterns = router.urls