from django.contrib import admin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'specialization', 'phone', 'created_at']
    search_fields = ['full_name', 'user__username', 'user__email']
    list_filter = ['specialization', 'created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Información de Usuario', {
            'fields': ('user',)
        }),
        ('Datos Personales', {
            'fields': ('full_name', 'specialization', 'phone')
        }),
        ('Registro', {
            'fields': ('created_at',)
        }),
    )
    
    def get_total_students(self, obj):
        return obj.get_total_students()
    get_total_students.short_description = 'Total Estudiantes'