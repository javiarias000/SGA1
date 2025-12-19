from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Activity,
    Asistencia,
    Calificacion,
    CalificacionParcial,
    Clase,
    Enrollment,
    GradeLevel,
    Horario,
    PromedioCache,
    TipoAporte,
)


@admin.register(GradeLevel) # Register GradeLevel
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ['level', 'section']
    search_fields = ['level', 'section']
    # If using autocomplete_fields elsewhere, this model needs a search_fields attribute



@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    # Removed 'teacher', added 'grade_level' and 'periodo'
    list_display = ['name', 'subject', 'grade_level', 'periodo', 'max_students', 'get_enrolled_count', 'active']
    # Removed 'teacher', added 'grade_level' and 'periodo'
    list_filter = ['subject', 'active', 'grade_level', 'periodo']
    # Removed 'teacher__full_name'
    search_fields = ['name']
    # Removed 'teacher', added 'grade_level'
    autocomplete_fields = ['subject', 'grade_level'] # Keep 'subject'

    # Fieldsets might need adjustment if 'teacher' was explicitly in them
    # For now, assuming no explicit 'teacher' in fieldsets, or it's handled implicitly

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'clase', 'docente', 'date_enrolled', 'estado']
    list_filter = ['estado', 'clase__subject', 'docente', 'clase__grade_level', 'clase__periodo', 'clase__ciclo_lectivo']
    search_fields = ['estudiante__nombre', 'clase__name', 'docente__nombre']
    autocomplete_fields = ['estudiante', 'clase', 'docente']

@admin.register(Horario) # New Admin class for Horario
class HorarioAdmin(admin.ModelAdmin):
    list_display = ['clase', 'dia_semana', 'hora_inicio', 'hora_fin']
    list_filter = ['dia_semana', 'clase__subject', 'clase__grade_level', 'clase__periodo']
    search_fields = ['clase__name', 'clase__subject__name']
    autocomplete_fields = ['clase']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'class_number', 'date', 'performance', 'get_teacher', 'created_at']
    list_filter = ['subject', 'performance', 'date']
    search_fields = ['student__usuario__nombre', 'topics_worked', 'pieces']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('student', 'subject', 'class_number', 'date')
        }),
        ('Contenido de la Clase', {
            'fields': ('topics_worked', 'techniques', 'pieces')
        }),
        ('Evaluación', {
            'fields': ('performance', 'strengths', 'areas_to_improve')
        }),
        ('Tareas', {
            'fields': ('homework', 'practice_time')
        }),
        ('Observaciones', {
            'fields': ('observations',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # This get_teacher method needs to be adapted since Clase no longer has a direct teacher
    # It should look for the teacher in the Enrollment related to this activity's student and clase
    def get_teacher(self, obj):
        if not obj.student.usuario:
            return "N/A"
        enrollment = obj.clase.enrollments.filter(estudiante=obj.student.usuario, estado='ACTIVO').first()
        if enrollment and enrollment.docente:
            return enrollment.docente.nombre
        return "N/A"
    get_teacher.short_description = 'Docente Asignado'






    
@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ['inscripcion', 'descripcion', 'nota', 'fecha']
    list_filter = ['fecha', 'inscripcion__clase__subject', 'inscripcion__clase__ciclo_lectivo']
    search_fields = ['inscripcion__estudiante__nombre', 'descripcion']
    autocomplete_fields = ['inscripcion']


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ['inscripcion', 'fecha', 'estado']
    list_filter = ['estado', 'fecha', 'inscripcion__clase__subject', 'inscripcion__clase__ciclo_lectivo']
    search_fields = ['inscripcion__estudiante__nombre', 'inscripcion__clase__name']
    autocomplete_fields = ['inscripcion']


@admin.register(TipoAporte)
class TipoAporteAdmin(admin.ModelAdmin):
    """Administración de tipos de aportes"""
    list_display = ['nombre', 'codigo', 'peso', 'orden', 'activo_badge', 'created_at']
    list_editable = ['peso', 'orden']
    list_filter = ['activo', 'created_at']
    search_fields = ['nombre', 'codigo', 'descripcion']
    ordering = ['orden', 'nombre']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('peso', 'orden', 'activo')
        }),
    )
    
    def activo_badge(self, obj):
        if obj.activo:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Activo</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Inactivo</span>'
        )
    activo_badge.short_description = 'Estado'
    
    def save_model(self, request, obj, form, change):
        """Validaciones adicionales al guardar"""
        super().save_model(request, obj, form, change)


@admin.register(CalificacionParcial)
class CalificacionParcialAdmin(admin.ModelAdmin):
    """Administración de calificaciones parciales"""
    list_display = [
        'student_nombre',
        'subject',
        'parcial_badge',
        'quimestre_badge',
        'tipo_aporte',
        'calificacion_badge',
        'escala_badge',
        'fecha_actualizacion'
    ]
    list_filter = [
        'parcial',
        'quimestre',
        'subject',
        'tipo_aporte',
        'fecha_registro',
        'registrado_por'
    ]
    search_fields = [
        'student__usuario__nombre',
        'observaciones'
    ]
    date_hierarchy = 'fecha_registro'
    readonly_fields = ['fecha_registro', 'fecha_actualizacion']
    autocomplete_fields = ['student', 'subject', 'tipo_aporte', 'registrado_por']
    
    fieldsets = (
        ('Información del Estudiante', {
            'fields': ('student', 'subject')
        }),
        ('Período Académico', {
            'fields': ('parcial', 'quimestre')
        }),
        ('Evaluación', {
            'fields': ('tipo_aporte', 'calificacion', 'observaciones'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('registrado_por', 'fecha_registro', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def student_nombre(self, obj):
        return obj.student.name
    student_nombre.short_description = 'Estudiante'
    student_nombre.admin_order_field = 'student__usuario__nombre'
    
    def parcial_badge(self, obj):
        colors = {
            '1P': '#3B82F6',
            '2P': '#8B5CF6',
            '3P': '#EC4899',
            '4P': '#F59E0B'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.parcial, '#6B7280'),
            obj.get_parcial_display()
        )
    parcial_badge.short_description = 'Parcial'
    
    def quimestre_badge(self, obj):
        color = '#10B981' if obj.quimestre == 'Q1' else '#F59E0B'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_quimestre_display()
        )
    quimestre_badge.short_description = 'Quimestre'
    
    def calificacion_badge(self, obj):
        return format_html(
            '<span style="font-size: 16px; font-weight: bold;">{}</span>',
            obj.calificacion
        )
    calificacion_badge.short_description = 'Nota'
    
    def escala_badge(self, obj):
        escala = obj.get_escala_cualitativa()
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            escala['color'],
            escala['text_color'],
            escala['codigo']
        )
    escala_badge.short_description = 'Escala'
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('student', 'student__usuario', 'subject', 'tipo_aporte', 'registrado_por', 'registrado_por__usuario')
    
    actions = ['calcular_promedios', 'exportar_excel']
    
    def calcular_promedios(self, request, queryset):
        """Acción para recalcular promedios"""
        estudiantes = set(q.student for q in queryset)
        count = 0
        for estudiante in estudiantes:
            # Forzar recálculo de cache
            promedio = CalificacionParcial.calcular_promedio_general(estudiante)
            count += 1
        
        self.message_user(
            request, 
            f"Promedios recalculados para {count} estudiante(s)"
        )
    calcular_promedios.short_description = "Recalcular promedios de estudiantes seleccionados"

#------------------------------------------------------------------


@admin.register(PromedioCache)
class PromedioCacheAdmin(admin.ModelAdmin):
    """Administración del cache de promedios"""
    list_display = [
        'student_nombre',
        'subject',
        'tipo_promedio_badge',
        'promedio_badge',
        'fecha_calculo'
    ]
    list_filter = [
        'tipo_promedio', 
        'subject',
        'fecha_calculo'
    ]
    search_fields = ['student__usuario__nombre']
    readonly_fields = ['fecha_calculo']
    date_hierarchy = 'fecha_calculo'
    
    def student_nombre(self, obj):
        return obj.student.name
    student_nombre.short_description = 'Estudiante'
    student_nombre.admin_order_field = 'student__usuario__nombre'
    
    def tipo_promedio_badge(self, obj):
        colors = {
            'parcial': '#3B82F6',
            'quimestre': '#8B5CF6',
            'general': '#10B981'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.tipo_promedio, '#6B7280'),
            obj.get_tipo_promedio_display()
        )
    tipo_promedio_badge.short_description = 'Tipo'
    
    def promedio_badge(self, obj):
        # Obtener escala cualitativa temporal
        nota = float(obj.promedio)
        if nota >= 9:
            color = '#10B981'
        elif nota >= 7:
            color = '#3B82F6'
        elif nota >= 4.01:
            color = '#F59E0B'
        else:
            color = '#EF4444'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; border-radius: 3px; font-size: 16px; font-weight: bold;">{}</span>',
            color,
            obj.promedio
        )
    promedio_badge.short_description = 'Promedio'
    
    def has_add_permission(self, request):
        """No permitir agregar manualmente (se genera automáticamente)"""
        return False
    
    actions = ['limpiar_cache']
    
    def limpiar_cache(self, request, queryset):
        """Acción para limpiar cache y regenerar"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f"{count} registro(s) de cache eliminados. Se regenerarán automáticamente."
        )
    limpiar_cache.short_description = "Limpiar cache seleccionado"