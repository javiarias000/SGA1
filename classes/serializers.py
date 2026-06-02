from rest_framework import serializers
from .models import (
    Clase, Enrollment, GradeLevel, TipoAporte, CalificacionParcial,
    Asistencia, Deber, DeberEntrega, Activity,
)
from subjects.models import Subject
from users.serializers import UsuarioSerializer

class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ['id', 'level', 'section', 'docente_tutor']
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
        fields = '__all__'
        read_only_fields = ['get_enrolled_count', 'has_space']

class EnrollmentSerializer(serializers.ModelSerializer):
    estudiante = UsuarioSerializer(read_only=True)
    clase = ClaseSerializer(read_only=True)
    docente = UsuarioSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'

# ─── TipoAporte ───────────────────────────────────────────────────────────────

class TipoAporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoAporte
        fields = ['id', 'nombre', 'codigo', 'descripcion', 'peso', 'orden', 'activo']

# ─── CalificacionParcial ──────────────────────────────────────────────────────

class CalificacionParcialSerializer(serializers.ModelSerializer):
    tipo_aporte_nombre = serializers.CharField(source='tipo_aporte.nombre', read_only=True)
    materia_nombre = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = CalificacionParcial
        fields = [
            'id', 'student', 'subject', 'materia_nombre', 'tipo_aporte', 'tipo_aporte_nombre',
            'parcial', 'quimestre', 'calificacion', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'materia_nombre', 'tipo_aporte_nombre']

# ─── Asistencia ───────────────────────────────────────────────────────────────

class AsistenciaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='inscripcion.estudiante.nombre', read_only=True)
    inscripcion_id = serializers.IntegerField(source='inscripcion.id', read_only=True)

    class Meta:
        model = Asistencia
        fields = ['id', 'inscripcion', 'inscripcion_id', 'estudiante_nombre', 'fecha', 'estado', 'observacion']

# ─── Activity ─────────────────────────────────────────────────────────────────

class ActivitySerializer(serializers.ModelSerializer):
    subject_nombre = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'student', 'clase', 'subject', 'subject_nombre', 'class_number', 'date',
            'topics_worked', 'techniques', 'pieces', 'performance',
            'strengths', 'areas_to_improve', 'homework', 'practice_time',
            'observations', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'class_number', 'subject_nombre']

# ─── Deber / DeberEntrega ─────────────────────────────────────────────────────

class DeberSerializer(serializers.ModelSerializer):
    entregas_completadas = serializers.IntegerField(read_only=True)
    porcentaje_entrega = serializers.FloatField(read_only=True)

    class Meta:
        model = Deber
        fields = [
            'id', 'titulo', 'descripcion', 'fecha_asignacion', 'fecha_entrega',
            'teacher', 'clase', 'puntos_totales', 'estado',
            'entregas_completadas', 'porcentaje_entrega',
        ]
        read_only_fields = ['id', 'fecha_asignacion', 'entregas_completadas', 'porcentaje_entrega']

class DeberEntregaSerializer(serializers.ModelSerializer):
    deber_titulo = serializers.CharField(source='deber.titulo', read_only=True)
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)

    class Meta:
        model = DeberEntrega
        fields = [
            'id', 'deber', 'deber_titulo', 'estudiante', 'estudiante_nombre',
            'fecha_entrega', 'comentario', 'calificacion', 'retroalimentacion', 'estado',
        ]
        read_only_fields = ['id', 'fecha_entrega', 'deber_titulo', 'estudiante_nombre']
