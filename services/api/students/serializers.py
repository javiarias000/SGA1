from rest_framework import serializers
from .models import Student
from users.serializers import UsuarioSerializer # Import from the central users app

class StudentSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True) # Nested serializer for Usuario details
    # Optionally include related fields like grade_level and teacher
    grade_level_name = serializers.CharField(source='grade_level.__str__', read_only=True)
    teacher_full_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'usuario', 'teacher', 'grade_level', 'parent_name', 
            'parent_email', 'parent_phone', 'notes', 'photo', 'active', 
            'registration_code', 'created_at', 'name', 
            'grade_level_name', 'teacher_full_name'
        ]
        read_only_fields = ['name', 'grade_level_name', 'teacher_full_name']
        extra_kwargs = {
            'teacher': {'write_only': True}, # Make teacher write-only if you don't want to expose the FK ID directly
            'grade_level': {'write_only': True} # Make grade_level write-only
        }