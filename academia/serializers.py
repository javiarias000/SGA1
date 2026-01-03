from rest_framework import serializers
from .models import Horario
from classes.models import GradeLevel, Subject
from users.serializers import UsuarioSerializer # Assuming UsuarioSerializer is in users.serializers

class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ['id', 'level', 'section', 'display_name']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'tipo_materia']

class HorarioSerializer(serializers.ModelSerializer):
    curso = GradeLevelSerializer(read_only=True)
    docente = UsuarioSerializer(read_only=True)
    clase = SubjectSerializer(read_only=True)

    class Meta:
        model = Horario
        fields = '__all__' # Include all fields from the Horario model