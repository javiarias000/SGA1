from celery import shared_task
from utils.notifications import NotificacionEmail
from students.models import Student
from classes.models import CalificacionParcial, Activity


@shared_task
def enviar_reportes_quimestrales():
    estudiantes = Student.objects.filter(active=True)
    for estudiante in estudiantes:
        if estudiante.parent_email:
            NotificacionEmail.enviar_reporte_calificaciones(
                estudiante,
                estudiante.parent_email,
            )


@shared_task
def verificar_rendimiento_semanal():
    estudiantes = Student.objects.filter(active=True)
    from classes.models import get_all_subjects
    for estudiante in estudiantes:
        for nombre in get_all_subjects():
            promedio = CalificacionParcial.calcular_promedio_quimestre(
                estudiante, nombre
            )
            if 0 < promedio < 7 and estudiante.parent_email:
                NotificacionEmail.enviar_alerta_bajo_rendimiento(
                    estudiante,
                    estudiante.parent_email,
                    nombre,
                )
