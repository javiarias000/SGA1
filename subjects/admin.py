from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Subject
from teachers.models import Teacher, TeacherSubject


class TeacherSubjectInline(admin.TabularInline):
    """Docentes que enseñan esta materia."""
    model = TeacherSubject
    extra = 1
    autocomplete_fields = ['teacher']
    verbose_name = 'Docente asignado'
    verbose_name_plural = '👩‍🏫 Docentes que enseñan esta materia'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__usuario')


class MallaCurricularInline(admin.TabularInline):
    """Niveles donde aparece esta materia en la malla."""
    model = None  # lazy import below
    extra = 0
    fields = ('nivel', 'obligatoria', 'orden')
    autocomplete_fields = ['nivel']
    readonly_fields = ('nivel',)
    verbose_name = 'Nivel en malla'
    verbose_name_plural = '📋 Niveles donde aparece (Malla Curricular)'
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        from classes.models import MallaCurricular
        return MallaCurricular.objects.filter().select_related('nivel')


# Lazy patch
def _patch_inline():
    from classes.models import MallaCurricular
    MallaCurricularInline.model = MallaCurricular

_patch_inline()


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ['name', 'get_tipo_badge', 'get_docentes_count',
                     'get_niveles_malla', 'get_clases_activas']
    list_filter   = ['tipo_materia']
    search_fields = ['name', 'description']
    ordering      = ['tipo_materia', 'name']
    inlines       = [TeacherSubjectInline, MallaCurricularInline]

    fieldsets = (
        ('Materia', {
            'fields': ('name', 'tipo_materia', 'description'),
        }),
    )

    TIPO_PALETTE = {
        'INSTRUMENTO': ('#92400e', '#fef3c7', '🎸'),
        'TEORIA':      ('#1e40af', '#eff6ff', '📖'),
        'AGRUPACION':  ('#065f46', '#ecfdf5', '🎵'),
        'OTRO':        ('#374151', '#f9fafb', '📝'),
    }

    def get_tipo_badge(self, obj):
        color, bg, icon = self.TIPO_PALETTE.get(obj.tipo_materia, ('#374151', '#f9fafb', '📝'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:5px;'
            'font-size:11px;font-weight:600;">{} {}</span>',
            bg, color, icon, obj.get_tipo_materia_display(),
        )
    get_tipo_badge.short_description = 'Tipo'
    get_tipo_badge.admin_order_field = 'tipo_materia'

    def get_docentes_count(self, obj):
        n = obj.teachers.count()
        if not n:
            return format_html('<span style="color:#9CA3AF">Sin docentes</span>')
        url = reverse('admin:teachers_teacher_changelist') + f'?subjects__id__exact={obj.pk}'
        return format_html('<a href="{}">{} docente{}</a>', url, n, 's' if n != 1 else '')
    get_docentes_count.short_description = 'Docentes'

    def get_niveles_malla(self, obj):
        entries = obj.malla_entries.select_related('nivel').order_by('nivel__level')
        if not entries.exists():
            return format_html('<span style="color:#9CA3AF">No está en malla</span>')
        niveles = ', '.join(e.nivel.get_level_display() for e in entries[:5])
        if entries.count() > 5:
            niveles += f' (+{entries.count()-5})'
        return niveles
    get_niveles_malla.short_description = 'En malla'

    def get_clases_activas(self, obj):
        n = obj.clases.filter(active=True).count()
        if not n:
            return '—'
        url = reverse('admin:classes_clase_changelist') + f'?subject__id__exact={obj.pk}&active__exact=1'
        return format_html('<a href="{}">{} clase{} activa{}</a>', url, n, 's' if n != 1 else '', 's' if n != 1 else '')
    get_clases_activas.short_description = 'Clases activas'
