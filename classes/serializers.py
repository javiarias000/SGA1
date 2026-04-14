from rest_framework import serializers
from .models import Clase, Enrollment, GradeLevel
from subjects.models import Subject
from users.serializers import UsuarioSerializer # From central users app

class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ['id', 'level', 'section', 'docente_tutor'] # Include docente_tutor
        read_only_fields = ['display_name']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'tipo_materia']

class ClaseSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    docente_base = UsuarioSerializer(read_only=True)
    grade_level = GradeLevelSerializer(read_only=True)
    
    class Meta:
        model = Clase
        fields = '__all__' # Adjust fields as needed
        read_only_fields = ['get_enrolled_count', 'has_space']

class EnrollmentSerializer(serializers.ModelSerializer):
    estudiante = UsuarioSerializer(read_only=True)
    clase = ClaseSerializer(read_only=True)
    docente = UsuarioSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ['get_estado_display'] # Example of a read-only property if it exists
