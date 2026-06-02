"""
Señales Django para disparar notificaciones WhatsApp automáticamente.

- CalificacionParcial post_save  → alerta si promedio quimestre < 7
- DeberEntrega post_save         → notifica al estudiante cuando se califica su entrega
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ─── Auto-matrícula al asignar nivel a un estudiante ─────────────────────────

@receiver(post_save, sender='students.Student')
def auto_matricular_por_malla(sender, instance, **kwargs):
    """
    Cuando se asigna un GradeLevel a un estudiante, crea automáticamente
    las Clases (si no existen) y los Enrollments para todas las materias
    obligatorias de la malla curricular de ese nivel.
    """
    try:
        from classes.models import GradeLevel, MallaCurricular, Clase, Enrollment
        from django.utils import timezone

        nivel = instance.grade_level
        usuario = instance.usuario

        if not nivel or not usuario:
            return

        ciclo_lectivo_actual = '2025-2026'  # TODO: variable de config global

        malla_entries = MallaCurricular.objects.filter(
            nivel=nivel,
            obligatoria=True,
        ).select_related('subject')

        for entry in malla_entries:
            subj = entry.subject

            # Buscar o crear la Clase para este nivel + materia + ciclo
            clase, clase_created = Clase.objects.get_or_create(
                subject=subj,
                grade_level=nivel,
                ciclo_lectivo=ciclo_lectivo_actual,
                defaults={
                    'name': f'{subj.name} — {nivel.get_level_display()} {ciclo_lectivo_actual}',
                    'active': True,
                    'docente_base': nivel.docente_tutor,
                },
            )
            if clase_created:
                logger.info('[auto_matricular] Clase creada: %s', clase)

            # Crear Enrollment si no existe
            enroll, enroll_created = Enrollment.objects.get_or_create(
                estudiante=usuario,
                clase=clase,
                defaults={
                    'estado': 'ACTIVO',
                    'docente': nivel.docente_tutor,
                },
            )
            if enroll_created:
                logger.info('[auto_matricular] Enrollment creado: %s → %s', usuario, clase)

    except Exception as exc:
        logger.exception('[auto_matricular] Error al auto-matricular estudiante %s: %s', instance.pk, exc)


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
