from rest_framework import serializers
from .models import Teacher
from users.serializers import UsuarioSerializer # Import from the central users app

class TeacherSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True) # Nested serializer for Usuario details

    class Meta:
        model = Teacher
        fields = ['id', 'usuario', 'specialization', 'photo', 'full_name']
        read_only_fields = ['full_name'] # full_name is a property, not a direct field