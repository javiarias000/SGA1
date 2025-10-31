from django.contrib import admin
from .models import Activity, Grade, Attendance, Clase, Enrollment, TipoAporte, CalificacionParcial, PromedioCache
from django.utils.html import format_html
    

@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'teacher', 'max_students', 'get_enrolled_count', 'active']
    list_filter = ['subject', 'active', 'teacher']
    search_fields = ['name', 'teacher__full_name']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'clase', 'date_enrolled', 'active']
    list_filter = ['active', 'clase__subject', 'clase__teacher']
    search_fields = ['student__name', 'clase__name', 'clase__teacher__full_name']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'class_number', 'date', 'performance', 'get_teacher', 'created_at']
    list_filter = ['subject', 'performance', 'date', 'student__teacher']
    search_fields = ['student__name', 'student__teacher__full_name', 'topics_worked', 'pieces']
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
    
    def get_teacher(self, obj):
        return obj.get_teacher().full_name
    get_teacher.short_description = 'Docente'


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'period', 'score', 'date', 'get_teacher']
    list_filter = ['subject', 'period', 'date', 'student__teacher']
    search_fields = ['student__name', 'student__teacher__full_name']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('student', 'subject', 'period', 'date')
        }),
        ('Calificación', {
            'fields': ('score', 'comments')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_teacher(self, obj):
        return obj.student.teacher.full_name
    get_teacher.short_description = 'Docente'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'status', 'get_teacher']
    list_filter = ['status', 'date', 'student__teacher']
    search_fields = ['student__name', 'student__teacher__full_name']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('student', 'date', 'status')
        }),
        ('Observaciones', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_teacher(self, obj):
        return obj.student.teacher.full_name
    get_teacher.short_description = 'Docente'

    


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
        'student__name', 
        'student__user__username',
        'observaciones'
    ]
    date_hierarchy = 'fecha_registro'
    readonly_fields = ['fecha_registro', 'fecha_actualizacion']
    autocomplete_fields = ['student', 'registrado_por']
    
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
    student_nombre.admin_order_field = 'student__name'
    
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
        return qs.select_related('student', 'tipo_aporte', 'registrado_por')
    
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
    search_fields = ['student__name']
    readonly_fields = ['fecha_calculo']
    date_hierarchy = 'fecha_calculo'
    
    def student_nombre(self, obj):
        return obj.student.name
    student_nombre.short_description = 'Estudiante'
    student_nombre.admin_order_field = 'student__name'
    
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