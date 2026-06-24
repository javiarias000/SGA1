from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Student
from classes.models import Enrollment, CalificacionParcial, Asistencia


class EnrollmentReadonlyInline(admin.TabularInline):
    """Inscripciones activas del estudiante (via Usuario FK)."""
    model = Enrollment
    fk_name = 'estudiante'         # FK en Enrollment apunta a Usuario
    extra = 0
    fields = ('clase', 'docente', 'tipo_materia', 'estado', 'date_enrolled')
    readonly_fields = ('clase', 'docente', 'tipo_materia', 'estado', 'date_enrolled')
    can_delete = False
    verbose_name = 'Inscripción'
    verbose_name_plural = '📚 Clases en las que está inscrito'
    show_change_link = True
    max_num = 0  # solo lectura, no añadir desde aquí

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(estado='ACTIVO').select_related(
            'clase__subject', 'clase__grade_level', 'docente',
        )

    # Adaptar FK: Enrollment.estudiante = Usuario, parent_obj = Student
    def get_object(self, request, object_id, from_field=None):
        return super().get_object(request, object_id, from_field)

    # Override para usar el usuario del student
    def get_formset(self, request, obj=None, **kwargs):
        fs = super().get_formset(request, obj, **kwargs)
        return fs


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display   = ['get_nombre', 'get_nivel_badge', 'get_ciclo',
                      'get_docente', 'active', 'get_clases_count',
                      'get_promedio', 'created_at']
    list_filter    = ['active', 'grade_level__ciclo', 'grade_level',
                      'teacher', 'created_at']
    search_fields  = ['usuario__nombre', 'usuario__cedula', 'usuario__email',
                      'parent_name', 'teacher__usuario__nombre']
    autocomplete_fields = ['usuario', 'teacher', 'grade_level']
    readonly_fields    = ['created_at', 'get_inscripciones_html', 'get_calificaciones_html']
    list_per_page      = 25
    date_hierarchy     = 'created_at'

    fieldsets = (
        ('Identidad', {
            'fields': ('usuario', 'active'),
        }),
        ('Ubicación académica', {
            'fields': ('grade_level', 'teacher'),
            'description': 'Al asignar un nivel, se inscribe automáticamente en las materias de la malla.',
        }),
        ('Representante', {
            'fields': ('parent_name', 'parent_email', 'parent_phone'),
        }),
        ('Datos adicionales', {
            'fields': ('notes', 'photo', 'created_at'),
            'classes': ('collapse',),
        }),
        ('📚 Inscripciones activas', {
            'fields': ('get_inscripciones_html',),
        }),
        ('📊 Últimas calificaciones', {
            'fields': ('get_calificaciones_html',),
        }),
    )

    # ─── Display methods ──────────────────────────────────────────────────────

    def get_nombre(self, obj):
        nombre = obj.name or '—'
        url = reverse('admin:students_student_change', args=[obj.pk])
        cedula = obj.usuario.cedula if obj.usuario else ''
        return format_html(
            '<a href="{}"><strong>{}</strong></a><br>'
            '<span style="font-size:11px;color:#6B7280">{}</span>',
            url, nombre, cedula or '',
        )
    get_nombre.short_description = 'Estudiante'
    get_nombre.admin_order_field = 'usuario__nombre'

    def get_nivel_badge(self, obj):
        if not obj.grade_level:
            return format_html('<span style="color:#9CA3AF">Sin nivel</span>')
        url = reverse('admin:classes_gradelevel_change', args=[obj.grade_level_id])
        return format_html('<a href="{}">{}</a>', url, obj.grade_level.get_level_display())
    get_nivel_badge.short_description = 'Nivel'
    get_nivel_badge.admin_order_field = 'grade_level__level'

    def get_ciclo(self, obj):
        if not obj.grade_level:
            return '—'
        from classes.admin import CICLO_COLORS
        color = CICLO_COLORS.get(obj.grade_level.ciclo, '#6B7280')
        return format_html(
            '<span style="border-left:3px solid {};padding-left:5px;font-size:11px">{}</span>',
            color, obj.grade_level.get_ciclo_display(),
        )
    get_ciclo.short_description = 'Ciclo'

    def get_docente(self, obj):
        if not obj.teacher:
            return '—'
        return obj.teacher.full_name
    get_docente.short_description = 'Docente'
    get_docente.admin_order_field = 'teacher__usuario__nombre'

    def get_clases_count(self, obj):
        if not obj.usuario:
            return '—'
        n = Enrollment.objects.filter(estudiante=obj.usuario, estado='ACTIVO').count()
        if n == 0:
            return format_html('<span style="color:#9CA3AF">0</span>')
        url = reverse('admin:classes_enrollment_changelist') + f'?estudiante__id__exact={obj.usuario_id}'
        return format_html('<a href="{}">{}</a>', url, n)
    get_clases_count.short_description = 'Clases'

    def get_promedio(self, obj):
        from classes.models import CalificacionParcial
        try:
            promedio = CalificacionParcial.calcular_promedio_general(obj)
            if promedio is None:
                return '—'
            from classes.admin import nota_badge
            return nota_badge(promedio)
        except Exception:
            return '—'
    get_promedio.short_description = 'Promedio'

    # ─── Readonly HTML fields ─────────────────────────────────────────────────

    def get_inscripciones_html(self, obj):
        if not obj.usuario:
            return '—'
        enrolls = Enrollment.objects.filter(
            estudiante=obj.usuario, estado='ACTIVO'
        ).select_related('clase__subject', 'clase__grade_level', 'docente')
        if not enrolls:
            return format_html('<em style="color:#9CA3AF">Sin inscripciones activas.</em>')
        rows = ''.join(
            f'<tr>'
            f'<td style="padding:4px 8px">{e.clase.name}</td>'
            f'<td style="padding:4px 8px">{e.clase.subject.name if e.clase.subject else "—"}</td>'
            f'<td style="padding:4px 8px">{e.docente.nombre if e.docente else "—"}</td>'
            f'<td style="padding:4px 8px">{e.tipo_materia}</td>'
            f'</tr>'
            for e in enrolls
        )
        return format_html(
            '<table style="width:100%;border-collapse:collapse;font-size:12px">'
            '<thead><tr style="background:#F9FAFB">'
            '<th style="padding:4px 8px;text-align:left">Clase</th>'
            '<th style="padding:4px 8px;text-align:left">Materia</th>'
            '<th style="padding:4px 8px;text-align:left">Docente</th>'
            '<th style="padding:4px 8px;text-align:left">Tipo</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            format_html(rows),
        )
    get_inscripciones_html.short_description = ''

    def get_calificaciones_html(self, obj):
        califs = CalificacionParcial.objects.filter(
            student=obj
        ).select_related('subject', 'tipo_aporte').order_by('subject__name', 'quimestre', 'parcial')[:20]
        if not califs:
            return format_html('<em style="color:#9CA3AF">Sin calificaciones registradas.</em>')
        from classes.admin import nota_badge
        rows = ''.join(
            f'<tr>'
            f'<td style="padding:3px 8px">{c.subject.name if c.subject else "—"}</td>'
            f'<td style="padding:3px 8px">{c.quimestre} {c.parcial}</td>'
            f'<td style="padding:3px 8px">{c.tipo_aporte.nombre if c.tipo_aporte else "—"}</td>'
            f'<td style="padding:3px 8px">{nota_badge(c.calificacion)}</td>'
            f'</tr>'
            for c in califs
        )
        return format_html(
            '<table style="width:100%;border-collapse:collapse;font-size:12px">'
            '<thead><tr style="background:#F9FAFB">'
            '<th style="padding:3px 8px;text-align:left">Materia</th>'
            '<th style="padding:3px 8px;text-align:left">Período</th>'
            '<th style="padding:3px 8px;text-align:left">Tipo Aporte</th>'
            '<th style="padding:3px 8px;text-align:left">Nota</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            format_html(rows),
        )
    get_calificaciones_html.short_description = ''

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'usuario', 'grade_level', 'teacher__usuario',
        )

    actions = ['inscribir_en_malla']

    @admin.action(description='📚 Re-aplicar malla curricular del nivel')
    def inscribir_en_malla(self, request, queryset):
        total = 0
        for student in queryset.select_related('grade_level', 'usuario'):
            # Re-trigger signal manually
            from classes.signals import auto_matricular_por_malla
            auto_matricular_por_malla(sender=Student, instance=student, created=False)
            total += 1
        self.message_user(request, f'Malla aplicada a {total} estudiante(s).')
