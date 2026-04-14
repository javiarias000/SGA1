from rest_framework import viewsets
from teachers.models import Teacher
from teachers.serializers import TeacherSerializer

class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Teacher.objects.all().select_related('usuario')
    serializer_class = TeacherSerializer