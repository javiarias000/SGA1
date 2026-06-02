from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from classes.models import (
    Clase, Enrollment, TipoAporte, CalificacionParcial,
    Asistencia, Deber, DeberEntrega, Activity,
)
from classes.serializers import (
    ClaseSerializer, EnrollmentSerializer, TipoAporteSerializer,
    CalificacionParcialSerializer, AsistenciaSerializer,
    DeberSerializer, DeberEntregaSerializer, ActivitySerializer,
)


class ClaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Clase.objects.all().select_related('subject', 'docente_base', 'grade_level')
    serializer_class = ClaseSerializer


class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Enrollment.objects.all().select_related('estudiante', 'clase', 'docente')
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        student = self.request.query_params.get('student')
        clase = self.request.query_params.get('clase')
        if student:
            qs = qs.filter(estudiante_id=student)
        if clase:
            qs = qs.filter(clase_id=clase)
        return qs


class TipoAporteViewSet(viewsets.ModelViewSet):
    queryset = TipoAporte.objects.filter(activo=True).order_by('orden', 'nombre')
    serializer_class = TipoAporteSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class CalificacionParcialViewSet(viewsets.ModelViewSet):
    serializer_class = CalificacionParcialSerializer

    def get_queryset(self):
        qs = CalificacionParcial.objects.select_related('subject', 'tipo_aporte', 'student')
        student = self.request.query_params.get('student')
        subject = self.request.query_params.get('subject')
        parcial = self.request.query_params.get('parcial')
        quimestre = self.request.query_params.get('quimestre')
        if student:
            qs = qs.filter(student_id=student)
        if subject:
            qs = qs.filter(subject__name__icontains=subject)
        if parcial:
            qs = qs.filter(parcial=parcial)
        if quimestre:
            qs = qs.filter(quimestre=quimestre)
        return qs


class AsistenciaViewSet(viewsets.ModelViewSet):
    serializer_class = AsistenciaSerializer

    def get_queryset(self):
        qs = Asistencia.objects.select_related('inscripcion__estudiante')
        student = self.request.query_params.get('student')
        inscripcion = self.request.query_params.get('inscripcion')
        fecha = self.request.query_params.get('fecha')
        if student:
            qs = qs.filter(inscripcion__estudiante_id=student)
        if inscripcion:
            qs = qs.filter(inscripcion_id=inscripcion)
        if fecha:
            qs = qs.filter(fecha=fecha)
        return qs


class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        qs = Activity.objects.select_related('subject', 'student', 'clase')
        student = self.request.query_params.get('student')
        clase = self.request.query_params.get('clase')
        subject = self.request.query_params.get('subject')
        if student:
            qs = qs.filter(student_id=student)
        if clase:
            qs = qs.filter(clase_id=clase)
        if subject:
            qs = qs.filter(subject_id=subject)
        return qs


class DeberViewSet(viewsets.ModelViewSet):
    serializer_class = DeberSerializer

    def get_queryset(self):
        qs = Deber.objects.select_related('teacher', 'clase')
        clase = self.request.query_params.get('clase')
        estado = self.request.query_params.get('estado')
        teacher = self.request.query_params.get('teacher')
        if clase:
            qs = qs.filter(clase_id=clase)
        if estado:
            qs = qs.filter(estado=estado)
        if teacher:
            qs = qs.filter(teacher_id=teacher)
        return qs

    @action(detail=True, methods=['get'], url_path='entregas')
    def entregas(self, request, pk=None):
        deber = self.get_object()
        entregas = DeberEntrega.objects.filter(deber=deber).select_related('estudiante')
        serializer = DeberEntregaSerializer(entregas, many=True)
        return Response(serializer.data)


class DeberEntregaViewSet(viewsets.ModelViewSet):
    serializer_class = DeberEntregaSerializer

    def get_queryset(self):
        qs = DeberEntrega.objects.select_related('deber', 'estudiante')
        deber = self.request.query_params.get('deber')
        estudiante = self.request.query_params.get('estudiante')
        if deber:
            qs = qs.filter(deber_id=deber)
        if estudiante:
            qs = qs.filter(estudiante_id=estudiante)
        return qs
