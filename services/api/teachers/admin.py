from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from .models import DirectorArea, DocenteFuncion, Funcion, Teacher, TeacherSubject


@admin.register(Funcion)
class FuncionAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'descripcion', 'activo']
    list_editable = ['activo']
    search_fields = ['nombre']


class DocenteFuncionInline(admin.TabularInline):
    """Funciones institucionales asignadas a este docente (Director de Área, Tutor, etc.)."""
    model = DocenteFuncion
    extra = 1
    autocomplete_fields = ['funcion']
    verbose_name = 'Función'
    verbose_name_plural = '🏷️ Funciones institucionales'


@admin.register(DocenteFuncion)
class DocenteFuncionAdmin(admin.ModelAdmin):
    list_display        = ['teacher', 'funcion', 'detalle', 'activo', 'created_at']
    list_filter          = ['funcion', 'activo']
    search_fields        = ['teacher__usuario__nombre', 'funcion__nombre', 'detalle']
    list_editable        = ['activo']
    autocomplete_fields = ['teacher', 'funcion']


@admin.register(DirectorArea)
class DirectorAreaAdmin(admin.ModelAdmin):
    list_display       = ['nombre', 'area', 'telefono', 'correo', 'activo']
    list_filter        = ['activo', 'area']
    search_fields      = ['nombre', 'area', 'correo', 'docente__nombre']
    list_editable      = ['activo']
    autocomplete_fields = ['docente']

    class Media:
        js = ['teachers/js/directorarea_autofill.js']

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        return [
            path('docente-data/', self.admin_site.admin_view(self._docente_data), name='directorarea_docente_data'),
        ] + urls

    def _docente_data(self, request):
        from django.http import JsonResponse
        from users.models import Usuario
        uid = request.GET.get('id', '').strip()
        if not uid:
            return JsonResponse({'error': 'missing id'}, status=400)
        try:
            u = Usuario.objects.select_related('teacher_profile').get(pk=uid)
            tp = getattr(u, 'teacher_profile', None)
            return JsonResponse({
                'nombre': u.nombre or '',
                'telefono': u.phone or '',
                'correo': u.email or '',
                'area': (tp.specialization if tp else '') or '',
            })
        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'not found'}, status=404)

    def save_model(self, request, obj, form, change):
        if obj.docente:
            u = obj.docente
            tp = getattr(u, 'teacher_profile', None)
            obj.nombre = u.nombre or obj.nombre
            obj.telefono = u.phone or obj.telefono
            obj.correo = u.email or obj.correo
            if not obj.area and tp:
                obj.area = tp.specialization or ''
        super().save_model(request, obj, form, change)


class TeacherSubjectInline(admin.TabularInline):
    """Materias que enseña este docente."""
    model = TeacherSubject
    extra = 1
    autocomplete_fields = ['subject']
    verbose_name = 'Materia'
    verbose_name_plural = '📚 Materias que enseña'


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display  = ['get_nombre', 'get_email', 'get_phone', 'specialization',
                     'get_materias', 'get_funciones', 'get_clases_activas', 'get_estudiantes_count', 'created_at']
    list_filter   = ['specialization', 'subjects', 'funciones__funcion', 'created_at']
    search_fields = ['usuario__nombre', 'usuario__email', 'usuario__cedula', 'specialization']
    autocomplete_fields = ['usuario']
    readonly_fields    = ['created_at', 'get_clases_html', 'get_estudiantes_html']
    list_per_page      = 20
    inlines            = [TeacherSubjectInline, DocenteFuncionInline]

    fieldsets = (
        ('Identidad', {
            'fields': ('usuario', 'specialization', 'photo'),
        }),
        ('Registro', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
        ('🏫 Clases que dicta', {
            'fields': ('get_clases_html',),
        }),
        ('👥 Estudiantes asignados', {
            'fields': ('get_estudiantes_html',),
        }),
    )

    # ─── Display methods ──────────────────────────────────────────────────────

    def get_nombre(self, obj):
        return format_html('<strong>{}</strong>', obj.full_name)
    get_nombre.short_description = 'Docente'
    get_nombre.admin_order_field = 'usuario__nombre'

    def get_email(self, obj):
        return obj.usuario.email if obj.usuario else '—'
    get_email.short_description = 'Email'

    def get_phone(self, obj):
        return obj.phone or '—'
    get_phone.short_description = 'Teléfono'

    def get_materias(self, obj):
        materias = obj.subjects.all()
        if not materias:
            return format_html('<span style="color:#9CA3AF">Sin materias</span>')
        return ', '.join(s.name for s in materias[:4])
    get_materias.short_description = 'Materias'

    def get_funciones(self, obj):
        funciones = obj.funciones.filter(activo=True).select_related('funcion')
        if not funciones:
            return format_html('<span style="color:#9CA3AF">—</span>')
        return format_html_join(
            ' ', '<span style="background:#EDE9FE;color:#6D28D9;padding:1px 6px;'
                 'border-radius:4px;font-size:11px;font-weight:600;margin-right:2px">{}</span>',
            ((f.funcion.nombre,) for f in funciones),
        )
    get_funciones.short_description = 'Funciones'

    def get_clases_activas(self, obj):
        if not obj.usuario:
            return '—'
        from classes.models import Clase
        n = Clase.objects.filter(docente_base=obj.usuario, active=True).count()
        if n == 0:
            return format_html('<span style="color:#9CA3AF">0</span>')
        url = reverse('admin:classes_clase_changelist') + f'?docente_base__id__exact={obj.usuario_id}&active__exact=1'
        return format_html('<a href="{}">{} clase{}</a>', url, n, 's' if n != 1 else '')
    get_clases_activas.short_description = 'Clases activas'

    def get_estudiantes_count(self, obj):
        n = obj.get_total_students()
        if n == 0:
            return '—'
        url = reverse('admin:students_student_changelist') + f'?teacher__id__exact={obj.pk}'
        return format_html('<a href="{}">{} estudiante{}</a>', url, n, 's' if n != 1 else '')
    get_estudiantes_count.short_description = 'Estudiantes'

    # ─── Readonly HTML fields ─────────────────────────────────────────────────

    def get_clases_html(self, obj):
        if not obj.usuario:
            return '—'
        from classes.models import Clase
        clases = Clase.objects.filter(
            docente_base=obj.usuario, active=True,
        ).select_related('subject', 'grade_level').order_by('grade_level__level', 'subject__name')
        if not clases:
            return format_html('<em style="color:#9CA3AF">Sin clases activas.</em>')
        rows = ''.join(
            f'<tr>'
            f'<td style="padding:4px 8px"><a href="{reverse("admin:classes_clase_change", args=[c.pk])}">{c.name}</a></td>'
            f'<td style="padding:4px 8px">{c.subject.name if c.subject else "—"}</td>'
            f'<td style="padding:4px 8px">{c.grade_level.get_level_display() if c.grade_level else "—"}</td>'
            f'<td style="padding:4px 8px">{c.ciclo_lectivo}</td>'
            f'<td style="padding:4px 8px">{c.enrollments.filter(estado="ACTIVO").count()} alumnos</td>'
            f'</tr>'
            for c in clases
        )
        return format_html(
            '<table style="width:100%;border-collapse:collapse;font-size:12px">'
            '<thead><tr style="background:#F9FAFB">'
            '<th style="padding:4px 8px;text-align:left">Clase</th>'
            '<th style="padding:4px 8px;text-align:left">Materia</th>'
            '<th style="padding:4px 8px;text-align:left">Nivel</th>'
            '<th style="padding:4px 8px;text-align:left">Ciclo lectivo</th>'
            '<th style="padding:4px 8px;text-align:left">Inscritos</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            format_html(rows),
        )
    get_clases_html.short_description = ''

    def get_estudiantes_html(self, obj):
        from students.models import Student
        estudiantes = Student.objects.filter(
            teacher=obj, active=True,
        ).select_related('usuario', 'grade_level').order_by('grade_level__level', 'usuario__nombre')
        if not estudiantes:
            return format_html('<em style="color:#9CA3AF">Sin estudiantes directos.</em>')
        rows = ''.join(
            f'<tr>'
            f'<td style="padding:4px 8px"><a href="{reverse("admin:students_student_change", args=[e.pk])}">'
            f'{e.usuario.nombre if e.usuario else e.pk}</a></td>'
            f'<td style="padding:4px 8px">{e.grade_level.get_level_display() if e.grade_level else "—"}</td>'
            f'</tr>'
            for e in estudiantes[:20]
        )
        extra = ''
        if estudiantes.count() > 20:
            extra = f'<tr><td colspan="2" style="padding:4px 8px;color:#6B7280">… y {estudiantes.count()-20} más</td></tr>'
        return format_html(
            '<table style="width:100%;border-collapse:collapse;font-size:12px">'
            '<thead><tr style="background:#F9FAFB">'
            '<th style="padding:4px 8px;text-align:left">Estudiante</th>'
            '<th style="padding:4px 8px;text-align:left">Nivel</th>'
            '</tr></thead><tbody>{}{}</tbody></table>',
            format_html(rows), format_html(extra),
        )
    get_estudiantes_html.short_description = ''

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario').prefetch_related(
            'subjects', 'funciones__funcion',
        )
