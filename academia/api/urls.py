from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    HorarioViewSet,
    enviar_alerta_rendimiento,
    enviar_reporte_calificaciones,
    enviar_reporte_docente,
    test_whatsapp,
)

router = DefaultRouter()
router.register(r'horarios', HorarioViewSet)

urlpatterns = router.urls + [
    # Notificaciones WhatsApp
    path(
        'notificaciones/reporte-estudiante/',
        enviar_reporte_calificaciones,
        name='notif_reporte_estudiante',
    ),
    path(
        'notificaciones/alerta-rendimiento/',
        enviar_alerta_rendimiento,
        name='notif_alerta_rendimiento',
    ),
    path(
        'notificaciones/reporte-docente/',
        enviar_reporte_docente,
        name='notif_reporte_docente',
    ),
    path(
        'notificaciones/test-whatsapp/',
        test_whatsapp,
        name='notif_test_whatsapp',
    ),
]
