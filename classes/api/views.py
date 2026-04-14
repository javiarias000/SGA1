from rest_framework import viewsets
from classes.models import Clase, Enrollment
from classes.serializers import ClaseSerializer, EnrollmentSerializer

class ClaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Clase.objects.all().select_related('subject', 'docente_base', 'grade_level')
    serializer_class = ClaseSerializer

class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Enrollment.objects.all().select_related('estudiante', 'clase', 'docente')
    serializer_class = EnrollmentSerializer