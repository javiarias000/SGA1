"""
Señales Django para disparar notificaciones WhatsApp automáticamente.

- CalificacionParcial post_save  → alerta si promedio quimestre < 7
- DeberEntrega post_save         → notifica al estudiante cuando se califica su entrega
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='classes.CalificacionParcial')
def alerta_bajo_rendimiento(sender, instance, created, **kwargs):
    """
    Tras guardar una calificación, recalcula el promedio del quimestre.
    Si queda por debajo de 7, envía alerta WhatsApp al representante.
    Solo actúa si el estudiante tiene un perfil Student asociado.
    """
    try:
        from classes.models import CalificacionParcial
        from utils.notifications import NotificacionWhatsApp

        student = instance.student
        materia = instance.subject
        quimestre = instance.quimestre

        promedio = float(CalificacionParcial.calcular_promedio_quimestre(
            student, materia, quimestre
        ))

        if 0 < promedio < 7:
            NotificacionWhatsApp.enviar_alerta_bajo_rendimiento(student, materia)
    except Exception as exc:
        logger.error(f'Signal alerta_bajo_rendimiento error: {exc}')


@receiver(post_save, sender='classes.DeberEntrega')
def notificar_calificacion_deber(sender, instance, created, **kwargs):
    """
    Cuando una entrega pasa a estado 'revisado' y tiene calificación,
    notifica al estudiante vía WhatsApp.
    """
    try:
        if instance.estado == 'revisado' and instance.calificacion is not None:
            from utils.notifications import NotificacionWhatsApp
            NotificacionWhatsApp.notificar_calificacion_deber(instance)
    except Exception as exc:
        logger.error(f'Signal notificar_calificacion_deber error: {exc}')
