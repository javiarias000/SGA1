from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade_level', 'teacher', 'active', 'get_class_count', 'created_at']
    list_filter = ['grade_level', 'active', 'teacher', 'created_at']
    search_fields = ['usuario__nombre', 'parent_name', 'teacher__usuario__nombre']
    readonly_fields = ['created_at']
    # filter_horizontal = ['subjects']

    fieldsets = (
        ('Información del Estudiante', {
            'fields': ('teacher', 'grade_level', 'active')
        }),
        ('Información de Contacto', {
            'fields': ('parent_name', 'parent_email', 'parent_phone')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )