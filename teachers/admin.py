from django.contrib import admin
from .models import Teacher
from classes.models import Curso, Clase, Deber, DeberEntrega

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'specialization', 'phone', 'created_at']
    search_fields = ['full_name', 'user__username', 'user__email']
    list_filter = ['specialization', 'created_at']
    readonly_fields = ['created_at']
    filter_horizontal = ['subjects']
    
    fieldsets = (
        ('Información de Usuario', {
            'fields': ('user',)
        }),
        ('Datos Personales', {
            'fields': ('full_name', 'specialization', 'phone', 'subjects')
        }),
        ('Registro', {
            'fields': ('created_at',)
        }),
    )
    
    def get_total_students(self, obj):
        return obj.get_total_students()
    get_total_students.short_description = 'Total Estudiantes'

# ============================================
# DEBERES
# ============================================



@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nivel', 'total_estudiantes']
    search_fields = ['nombre', 'nivel']
    filter_horizontal = ['estudiantes']
    
    def total_estudiantes(self, obj):
        return obj.estudiantes.count()
    total_estudiantes.short_description = 'Estudiantes'

@admin.register(Deber)
class DeberAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'clase', 'teacher', 'fecha_entrega', 'estado', 'porcentaje_entrega']
    list_filter = ['estado', 'clase', 'fecha_entrega']
    search_fields = ['titulo', 'descripcion']
    filter_horizontal = ['cursos', 'estudiantes_especificos']
    date_hierarchy = 'fecha_entrega'
    
    def porcentaje_entrega(self, obj):
        return f"{obj.porcentaje_entrega()}%"
    porcentaje_entrega.short_description = 'Progreso'

@admin.register(DeberEntrega)
class DeberEntregaAdmin(admin.ModelAdmin):
    list_display = ['deber', 'estudiante', 'fecha_entrega', 'calificacion', 'estado']
    list_filter = ['estado', 'deber']
    search_fields = ['deber__titulo', 'estudiante__username', 'estudiante__first_name']
    readonly_fields = ['fecha_entrega', 'fecha_actualizacion']