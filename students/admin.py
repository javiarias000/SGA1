from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade', 'teacher', 'active', 'get_class_count', 'created_at']
    list_filter = ['grade', 'active', 'teacher', 'created_at']
    search_fields = ['name', 'parent_name', 'teacher__full_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Información del Estudiante', {
            'fields': ('teacher', 'name', 'grade', 'active')
        }),
        ('Información de Contacto', {
            'fields': ('parent_name', 'parent_email', 'parent_phone')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_class_count(self, obj):
        return obj.get_class_count()
    get_class_count.short_description = 'Clases Registradas'