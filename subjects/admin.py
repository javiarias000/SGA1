from django.contrib import admin
from .models import Subject
from teachers.models import Teacher, TeacherSubject # Import Teacher and the new TeacherSubject model

class TeacherInline(admin.TabularInline):
    model = TeacherSubject # Use the explicit through model
    extra = 1 # Number of empty forms to display
    autocomplete_fields = ['teacher'] # This field links to the Teacher model

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'tipo_materia', 'get_teacher_count', 'description')
    list_filter = ('tipo_materia',)
    search_fields = ('name', 'description')
    inlines = [TeacherInline] # Add the inline here

    def get_teacher_count(self, obj):
        return obj.teachers.count()
    get_teacher_count.short_description = 'Número de Docentes'