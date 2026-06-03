from django import template

register = template.Library()


@register.simple_tag
def get_dashboard_stats():
    from users.models import Usuario
    from classes.models import Enrollment, Clase
    from matriculas.models import SolicitudMatricula

    return {
        'total_estudiantes': Usuario.objects.filter(rol='ESTUDIANTE').count(),
        'total_docentes': Usuario.objects.filter(rol='DOCENTE').count(),
        'clases_activas': Clase.objects.filter(active=True).count(),
        'inscripciones_activas': Enrollment.objects.filter(estado='ACTIVO').count(),
        'solicitudes_pendientes': SolicitudMatricula.objects.filter(estado='PENDIENTE').count(),
        'solicitudes_revision': SolicitudMatricula.objects.filter(estado='EN_REVISION').count(),
    }
