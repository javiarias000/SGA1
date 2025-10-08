from django.contrib import admin
from .models import Teacher, Student, Activity, Grade, Attendance

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'specialization', 'phone', 'get_total_students', 'created_at']
    list_filter = ['specialization', 'created_at']
    search_fields = ['full_name', 'user__username', 'user__email']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('user',)
        }),
        ('Información Personal', {
            'fields': ('full_name', 'specialization', 'phone')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_students(self, obj):
        return obj.get_total_students()
    get_total_students.short_description = 'Total Estudiantes'


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