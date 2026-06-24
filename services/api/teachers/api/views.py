from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from teachers.models import Teacher
from teachers.serializers import TeacherSerializer
from classes.models import CalificacionParcial, Asistencia, Enrollment
from classes.serializers import CalificacionParcialSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all().select_related('usuario')
    serializer_class = TeacherSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(usuario__nombre__icontains=search)
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def libreta_estudiante_api(request, student_id):
    """Return a student's complete grade report grouped by subject and parcial."""
    from students.models import Student
    try:
        student = Student.objects.select_related('usuario').get(pk=student_id)
    except Student.DoesNotExist:
        return Response({'detail': 'Estudiante no encontrado.'}, status=404)

    calificaciones = CalificacionParcial.objects.filter(
        student=student
    ).select_related('subject', 'tipo_aporte').order_by('subject__name', 'quimestre', 'parcial')

    asistencias = Asistencia.objects.filter(
        inscripcion__estudiante=student.usuario
    ).select_related('inscripcion__clase__subject').order_by('-fecha')

    # Group grades by subject → quimestre → parcial
    materias: dict = {}
    for c in calificaciones:
        sname = c.subject.name if c.subject else 'Sin materia'
        materias.setdefault(sname, []).append({
            'id': c.id,
            'parcial': c.parcial,
            'quimestre': c.quimestre,
            'tipo_aporte': c.tipo_aporte.nombre if c.tipo_aporte else '',
            'calificacion': float(c.calificacion),
        })

    promedio_general = None
    all_vals = [float(c.calificacion) for c in calificaciones]
    if all_vals:
        promedio_general = round(sum(all_vals) / len(all_vals), 2)

    total_asist = asistencias.count()
    presentes = asistencias.filter(estado='Presente').count()
    ausentes = asistencias.filter(estado='Ausente').count()
    justificados = asistencias.filter(estado='Justificado').count()

    return Response({
        'student_id': student.id,
        'nombre': student.usuario.nombre if student.usuario else '',
        'promedio_general': promedio_general,
        'materias': materias,
        'asistencia': {
            'total': total_asist,
            'presentes': presentes,
            'ausentes': ausentes,
            'justificados': justificados,
            'porcentaje': round(presentes / total_asist * 100, 1) if total_asist else 0,
        },
    })