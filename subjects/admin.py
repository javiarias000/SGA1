from django.contrib import admin
from .models import Subject
from teachers.models import Teacher, TeacherSubject  # Import Teacher and the new TeacherSubject model

class TeacherInline(admin.TabularInline):
    model = TeacherSubject  # Use the explicit through model
    extra = 1  # Number of empty forms to display
    autocomplete_fields = ['teacher']  # This field links to the Teacher model

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'tipo_materia', 'get_niveles_malla', 'get_teacher_count')
    list_filter = ('tipo_materia',)
    search_fields = ('name', 'description')
    inlines = [TeacherInline]
    ordering = ['tipo_materia', 'name']

    def get_niveles_malla(self, obj):
        entries = obj.malla_entries.select_related('nivel').order_by('nivel__level')
        if not entries.exists():
            return '—'
        niveles = ', '.join(e.nivel.get_level_display() for e in entries[:5])
        if entries.count() > 5:
            niveles += f' (+{entries.count() - 5} más)'
        return niveles
    get_niveles_malla.short_description = 'En niveles'

    def get_teacher_count(self, obj):
        count = obj.teachers.count()
        return f'{count} docente{"s" if count != 1 else ""}'
    get_teacher_count.short_description = 'Docentes'