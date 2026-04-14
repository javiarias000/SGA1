from rest_framework import viewsets
from students.models import Student
from students.serializers import StudentSerializer

class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Student.objects.all().select_related('usuario', 'grade_level', 'teacher__usuario') # Prefetch related data
    serializer_class = StudentSerializer