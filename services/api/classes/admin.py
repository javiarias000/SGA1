"""
Admin del módulo de Clases.

Flujo académico:
  GradeLevel → MallaCurricular → Clase → Enrollment → Asistencia / CalificacionParcial
                                       → Deber       → DeberEntrega
"""
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect

from .models import (
    GradeLevel, MallaCurricular,
    Clase, Enrollment, Horario,
    TipoAporte, CalificacionParcial, Asistencia,
    Activity, Deber, DeberEntrega, PromedioCache,
)
from subjects.models import Subject


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

CICLO_COLORS = {
    'BASICA':        '#059669',
    'MEDIA':         '#2563EB',
    'SUPERIOR':      '#7C3AED',
    'BACHILLERATO':  '#D97706',
}

GRADE_COLORS = {
    'DAR':  ('#dcfce7', '#166534'),  # ≥9
    'AAR':  ('#dbeafe', '#1e40af'),  # ≥7
    'PAAR': ('#fef9c3', '#854d0e'),  # ≥4
    'NAAR': ('#fee2e2', '#991b1b'),  # <4
}

def nota_badge(nota):
    if nota is None:
        return '—'
    n = float(nota)
    if n >= 9:   label, (bg, fg) = 'DAR',  GRADE_COLORS['DAR']
    elif n >= 7: label, (bg, fg) = 'AAR',  GRADE_COLORS['AAR']
    elif n >= 4: label, (bg, fg) = 'PAAR', GRADE_COLORS['PAAR']
    else:        label, (bg, fg) = 'NAAR', GRADE_COLORS['NAAR']
    return format_html(
        '<span style="background:{};color:{};padding:2px 8px;border-radius:5px;'
        'font-size:11px;font-weight:700;">{} {}</span>',
        bg, fg, n, label,
    )

def estado_badge(texto, color='#6B7280', bg='#F3F4F6'):
    return format_html(
        '<span style="background:{};color:{};padding:2px 8px;border-radius:5px;'
        'font-size:11px;font-weight:600;">{}</span>',
        bg, color, texto,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INLINES REUTILIZABLES
# ═══════════════════════════════════════════════════════════════════════════════

class MallaCurricularInline(admin.TabularInline):
    model = MallaCurricular
    extra = 1
    fields = ('subject', 'obligatoria', 'orden')
    autocomplete_fields = ['subject']
    ordering = ('orden', 'subject__name')
    verbose_name = 'Materia en malla'
    verbose_name_plural = '📚 Materias de este nivel'


class EnrollmentInline(admin.TabularInline):
    """Estudiantes inscritos en una Clase."""
    model = Enrollment
    extra = 0
    fields = ('estudiante', 'docente', 'tipo_materia', 'estado', 'date_enrolled')
    autocomplete_fields = ['estudiante', 'docente']
    readonly_fields = ('date_enrolled',)
    verbose_name = 'Inscripción'
    verbose_name_plural = '👥 Estudiantes inscritos'
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('estudiante', 'docente')


class HorarioInline(admin.TabularInline):
    model = Horario
    extra = 1
    fields = ('dia_semana', 'hora_inicio', 'hora_fin')
    verbose_name = 'Horario'
    verbose_name_plural = '🕐 Horarios'


class DeberInline(admin.TabularInline):
    model = Deber
    extra = 0
    fields = ('titulo', 'fecha_entrega', 'estado')
    readonly_fields = ('fecha_entrega',)
    show_change_link = True
    verbose_name = 'Deber'
    verbose_name_plural = '📝 Deberes asignados'


class AsistenciaInline(admin.TabularInline):
    """Asistencia para un Enrollment."""
    model = Asistencia
    extra = 0
    fields = ('fecha', 'estado', 'observacion')
    ordering = ('-fecha',)
    verbose_name = 'Asistencia'
    verbose_name_plural = '✅ Registros de asistencia'

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-fecha')[:20]


class DeberEntregaInline(admin.TabularInline):
    model = DeberEntrega
    extra = 0
    fields = ('estudiante', 'estado', 'calificacion', 'retroalimentacion', 'fecha_entrega')
    readonly_fields = ('fecha_entrega',)
    autocomplete_fields = ['estudiante']
    verbose_name = 'Entrega'
    verbose_name_plural = '📬 Entregas recibidas'
    show_change_link = True


# ═══════════════════════════════════════════════════════════════════════════════
# GRADE LEVEL  (Estructura del programa)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display  = ['get_nivel_badge', 'section', 'get_ciclo_badge',
                     'docente_tutor', 'get_malla_count', 'get_estudiantes_count', 'get_clases_count']
    list_filter   = ['ciclo', 'level']
    search_fields = ['level', 'section', 'docente_tutor__nombre']
    autocomplete_fields = ['docente_tutor']
    inlines       = [MallaCurricularInline]
    ordering      = ['level', 'section']

    fieldsets = (
        ('Identificación', {
            'fields': ('level', 'ciclo', 'section'),
        }),
        ('Docente tutor', {
            'fields': ('docente_tutor',),
        }),
    )

    def get_nivel_badge(self, obj):
        return format_html('<strong>{}</strong>', obj.get_level_display())
    get_nivel_badge.short_description = 'Nivel'
    get_nivel_badge.admin_order_field = 'level'

    def get_ciclo_badge(self, obj):
        color = CICLO_COLORS.get(obj.ciclo, '#6B7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 9px;border-radius:5px;font-size:11px;font-weight:700;">{}</span>',
            color, obj.get_ciclo_display(),
        )
    get_ciclo_badge.short_description = 'Ciclo'
    get_ciclo_badge.admin_order_field = 'ciclo'

    def get_malla_count(self, obj):
        n = obj.malla_curricular.count()
        url = reverse('admin:classes_mallacurricular_changelist') + f'?nivel__id__exact={obj.pk}'
        return format_html('<a href="{}">{} materia{}</a>', url, n, 's' if n != 1 else '')
    get_malla_count.short_description = 'Malla'

    def get_estudiantes_count(self, obj):
        n = obj.students.count()
        url = reverse('admin:students_student_changelist') + f'?grade_level__id__exact={obj.pk}'
        return format_html('<a href="{}">{} estudiante{}</a>', url, n, 's' if n != 1 else '')
    get_estudiantes_count.short_description = 'Estudiantes'

    def get_clases_count(self, obj):
        n = obj.clases.count()
        url = reverse('admin:classes_clase_changelist') + f'?grade_level__id__exact={obj.pk}'
        return format_html('<a href="{}">{} clase{}</a>', url, n, 's' if n != 1 else '')
    get_clases_count.short_description = 'Clases'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('malla-curricular/', self.admin_site.admin_view(self.malla_view),
                 name='classes_gradelevel_malla'),
            path('<int:nivel_id>/aplicar-malla-defecto/', self.admin_site.admin_view(self.aplicar_malla_defecto),
                 name='classes_gradelevel_aplicar_malla'),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['planificacion_url'] = '/classes/planificacion/'
        extra_context['malla_url'] = reverse('admin:classes_gradelevel_malla')
        return super().changelist_view(request, extra_context=extra_context)

    def malla_view(self, request):
        from django.db.models import Prefetch
        ciclos = {}
        for ciclo_key, ciclo_label in GradeLevel.CICLO_CHOICES:
            niveles = GradeLevel.objects.filter(ciclo=ciclo_key).prefetch_related(
                Prefetch('malla_curricular',
                         queryset=MallaCurricular.objects.select_related('subject').order_by('orden', 'subject__name'))
            ).order_by('level')
            if niveles.exists():
                ciclos[ciclo_label] = niveles
        ctx = {
            **self.admin_site.each_context(request),
            'title': 'Malla Curricular',
            'ciclos': ciclos,
            'opts': self.model._meta,
        }
        return render(request, 'admin/classes/malla_curricular.html', ctx)

    def aplicar_malla_defecto(self, request, nivel_id):
        from classes.management.commands.cargar_malla_default import MALLA_POR_CICLO
        try:
            nivel = GradeLevel.objects.get(pk=nivel_id)
        except GradeLevel.DoesNotExist:
            messages.error(request, 'Nivel no encontrado.')
            return HttpResponseRedirect(reverse('admin:classes_gradelevel_malla'))
        creadas = 0
        with transaction.atomic():
            for nombre, obligatoria, orden in MALLA_POR_CICLO.get(nivel.ciclo, []):
                try:
                    subj = Subject.objects.get(name=nombre)
                except Subject.DoesNotExist:
                    continue
                _, created = MallaCurricular.objects.get_or_create(
                    nivel=nivel, subject=subj,
                    defaults={'obligatoria': obligatoria, 'orden': orden},
                )
                if created:
                    creadas += 1
        messages.success(request, f'Malla aplicada a {nivel}: {creadas} materias nuevas añadidas.')
        return HttpResponseRedirect(reverse('admin:classes_gradelevel_malla'))


# ═══════════════════════════════════════════════════════════════════════════════
# MALLA CURRICULAR
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(MallaCurricular)
class MallaCurricularAdmin(admin.ModelAdmin):
    list_display  = ['get_nivel_display', 'get_ciclo_badge', 'subject', 'get_tipo', 'obligatoria', 'orden']
    list_filter   = ['nivel__ciclo', 'obligatoria', 'subject__tipo_materia', 'nivel__level']
    search_fields = ['nivel__level', 'nivel__section', 'subject__name']
    autocomplete_fields = ['nivel', 'subject']
    list_editable = ['obligatoria', 'orden']
    ordering      = ['nivel__level', 'orden', 'subject__name']

    def get_nivel_display(self, obj):
        return str(obj.nivel)
    get_nivel_display.short_description = 'Nivel'
    get_nivel_display.admin_order_field = 'nivel__level'

    def get_ciclo_badge(self, obj):
        color = CICLO_COLORS.get(obj.nivel.ciclo, '#6B7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 7px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.nivel.get_ciclo_display(),
        )
    get_ciclo_badge.short_description = 'Ciclo'

    def get_tipo(self, obj):
        icons = {'INSTRUMENTO': '🎸', 'TEORIA': '📖', 'AGRUPACION': '🎵', 'OTRO': '📝'}
        return f"{icons.get(obj.subject.tipo_materia, '📝')} {obj.subject.get_tipo_materia_display()}"
    get_tipo.short_description = 'Tipo'


# ═══════════════════════════════════════════════════════════════════════════════
# TIPO DE APORTE  (Ponderación de calificaciones)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(TipoAporte)
class TipoAporteAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'codigo', 'peso', 'orden', 'activo']
    list_filter   = ['activo']
    search_fields = ['nombre', 'codigo']
    list_editable = ['peso', 'orden', 'activo']
    ordering      = ['orden', 'nombre']


# ═══════════════════════════════════════════════════════════════════════════════
# CLASE  (Instancia de materia para un nivel y docente)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display  = ['get_nombre', 'subject', 'get_nivel', 'docente_base',
                     'ciclo_lectivo', 'get_inscritos', 'active', 'get_importar_link']
    list_filter   = ['active', 'ciclo_lectivo', 'subject__tipo_materia',
                     'grade_level__ciclo', 'grade_level']
    search_fields = ['name', 'subject__name', 'docente_base__nombre',
                     'grade_level__level', 'grade_level__section']
    autocomplete_fields = ['subject', 'grade_level', 'docente_base']
    list_per_page = 25
    inlines       = [EnrollmentInline, HorarioInline, DeberInline]

    fieldsets = (
        ('Identificación', {
            'fields': ('name', 'subject', 'grade_level'),
        }),
        ('Docente y ciclo', {
            'fields': ('docente_base', 'ciclo_lectivo', 'paralelo', 'periodo'),
        }),
        ('Detalles', {
            'fields': ('description', 'schedule', 'room', 'max_students', 'active'),
            'classes': ('collapse',),
        }),
    )

    def get_nombre(self, obj):
        return format_html('<strong>{}</strong>', obj.name)
    get_nombre.short_description = 'Clase'
    get_nombre.admin_order_field = 'name'

    def get_nivel(self, obj):
        if not obj.grade_level:
            return '—'
        color = CICLO_COLORS.get(obj.grade_level.ciclo, '#6B7280')
        return format_html(
            '<span style="border-left:3px solid {};padding-left:6px">{}</span>',
            color, obj.grade_level,
        )
    get_nivel.short_description = 'Nivel'
    get_nivel.admin_order_field = 'grade_level__level'

    def get_inscritos(self, obj):
        n = obj.enrollments.filter(estado='ACTIVO').count()
        mx = obj.max_students
        pct = n / mx * 100 if mx else 0
        color = '#DC2626' if pct >= 90 else '#D97706' if pct >= 70 else '#059669'
        url = reverse('admin:classes_enrollment_changelist') + f'?clase__id__exact={obj.pk}'
        return format_html(
            '<a href="{}" style="color:{}">{}/{}</a>', url, color, n, mx,
        )
    get_inscritos.short_description = 'Inscritos'

    def get_importar_link(self, obj):
        url = reverse('admin:classes_clase_importar_calificaciones', args=[obj.pk])
        return format_html('<a href="{}">📥 Importar notas</a>', url)
    get_importar_link.short_description = 'Calificaciones'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'subject', 'grade_level', 'docente_base',
        ).annotate(total_inscritos=Count('enrollments'))

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:clase_id>/importar-calificaciones/',
                 self.admin_site.admin_view(self.importar_calificaciones_view),
                 name='classes_clase_importar_calificaciones'),
        ]
        return custom + urls

    def importar_calificaciones_view(self, request, clase_id):
        import json as json_lib
        from informes.import_calificaciones import parse_workbook, importar_calificaciones

        clase = self.get_object(request, clase_id)
        if clase is None:
            messages.error(request, 'Clase no encontrada.')
            return HttpResponseRedirect(reverse('admin:classes_clase_changelist'))

        ctx = {
            **self.admin_site.each_context(request),
            'title': f'Importar calificaciones — {clase}',
            'clase': clase,
            'opts': self.model._meta,
            'resumen': None,
            'confirmado': False,
            'parsed_json': '',
        }

        if request.method == 'POST':
            parsed_json = request.POST.get('parsed_json')
            confirmar = request.POST.get('confirmar') == '1'

            # Paso 2: ya hubo vista previa, el usuario confirmó la importación real.
            if confirmar and parsed_json:
                try:
                    parsed = json_lib.loads(parsed_json)
                except ValueError:
                    messages.error(request, 'Datos de importación inválidos, vuelve a subir el archivo.')
                    return render(request, 'admin/classes/importar_calificaciones.html', ctx)
                resumen = importar_calificaciones(clase, parsed, dry_run=False)
                ctx['resumen'] = resumen
                ctx['confirmado'] = True
                messages.success(
                    request,
                    f"Importación completada: {resumen['notas_creadas']} notas creadas, "
                    f"{resumen['notas_actualizadas']} actualizadas, "
                    f"{resumen['telefonos_actualizados']} teléfonos rellenados."
                )
                return render(request, 'admin/classes/importar_calificaciones.html', ctx)

            # Paso 1: subieron un archivo nuevo, mostrar vista previa (dry run).
            archivo = request.FILES.get('archivo')
            if not archivo:
                messages.error(request, 'Selecciona un archivo .xlsx para continuar.')
                return render(request, 'admin/classes/importar_calificaciones.html', ctx)

            import openpyxl
            try:
                wb = openpyxl.load_workbook(archivo, data_only=True)
            except Exception as exc:
                messages.error(request, f'No se pudo leer el archivo: {exc}')
                return render(request, 'admin/classes/importar_calificaciones.html', ctx)

            parsed = parse_workbook(wb)
            resumen = importar_calificaciones(clase, parsed, dry_run=True)
            ctx['resumen'] = resumen
            ctx['parsed_json'] = json_lib.dumps(parsed, default=str)

        return render(request, 'admin/classes/importar_calificaciones.html', ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# ENROLLMENT  (Vínculo estudiante ↔ clase ↔ docente)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display  = ['get_estudiante', 'get_clase', 'get_docente',
                     'tipo_materia', 'get_estado_badge', 'date_enrolled']
    list_filter   = ['estado', 'tipo_materia', 'clase__subject__tipo_materia',
                     'clase__grade_level__ciclo', 'clase__ciclo_lectivo']
    search_fields = ['estudiante__nombre', 'clase__name', 'clase__subject__name',
                     'docente__nombre']
    autocomplete_fields = ['estudiante', 'clase', 'docente']
    readonly_fields   = ['date_enrolled']
    inlines           = [AsistenciaInline]
    date_hierarchy    = 'date_enrolled'
    list_per_page     = 30

    fieldsets = (
        ('Inscripción', {
            'fields': ('estudiante', 'clase', 'docente', 'tipo_materia', 'estado'),
        }),
        ('Metadata', {
            'fields': ('date_enrolled',),
            'classes': ('collapse',),
        }),
    )

    def get_estudiante(self, obj):
        url = reverse('admin:students_student_changelist') + f'?usuario__id__exact={obj.estudiante_id}'
        return format_html('<a href="{}">{}</a>', url, obj.estudiante.nombre if obj.estudiante else '—')
    get_estudiante.short_description = 'Estudiante'
    get_estudiante.admin_order_field = 'estudiante__nombre'

    def get_clase(self, obj):
        if not obj.clase:
            return '—'
        url = reverse('admin:classes_clase_change', args=[obj.clase_id])
        return format_html('<a href="{}">{}</a>', url, obj.clase.name)
    get_clase.short_description = 'Clase'
    get_clase.admin_order_field = 'clase__name'

    def get_docente(self, obj):
        return obj.docente.nombre if obj.docente else '—'
    get_docente.short_description = 'Docente'

    def get_estado_badge(self, obj):
        if obj.estado == 'ACTIVO':
            return estado_badge('ACTIVO', '#166534', '#dcfce7')
        return estado_badge('RETIRADO', '#991b1b', '#fee2e2')
    get_estado_badge.short_description = 'Estado'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'estudiante', 'clase__subject', 'clase__grade_level', 'docente',
        )

    actions = ['marcar_activo', 'marcar_retirado']

    @admin.action(description='✅ Marcar seleccionados como ACTIVO')
    def marcar_activo(self, request, queryset):
        n = queryset.update(estado='ACTIVO')
        self.message_user(request, f'{n} inscripción(es) marcadas como ACTIVO.')

    @admin.action(description='❌ Marcar seleccionados como RETIRADO')
    def marcar_retirado(self, request, queryset):
        n = queryset.update(estado='RETIRADO')
        self.message_user(request, f'{n} inscripción(es) marcadas como RETIRADO.')


# ═══════════════════════════════════════════════════════════════════════════════
# HORARIO
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display  = ['clase', 'dia_semana', 'hora_inicio', 'hora_fin']
    list_filter   = ['dia_semana', 'clase__grade_level__ciclo']
    search_fields = ['clase__name', 'clase__subject__name']
    autocomplete_fields = ['clase']
    ordering      = ['dia_semana', 'hora_inicio']


# ═══════════════════════════════════════════════════════════════════════════════
# CALIFICACIÓN PARCIAL
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(CalificacionParcial)
class CalificacionParcialAdmin(admin.ModelAdmin):
    list_display  = ['get_estudiante', 'subject', 'parcial', 'quimestre',
                     'tipo_aporte', 'get_nota_badge', 'registrado_por', 'fecha_actualizacion']
    list_filter   = ['parcial', 'quimestre', 'tipo_aporte', 'subject',
                     'student__grade_level__ciclo', 'student__grade_level']
    search_fields = ['student__usuario__nombre', 'subject__name', 'registrado_por__usuario__nombre']
    autocomplete_fields = ['student', 'subject', 'tipo_aporte', 'registrado_por']
    readonly_fields   = ['fecha_registro', 'fecha_actualizacion']
    date_hierarchy    = 'fecha_actualizacion'
    list_per_page     = 30

    fieldsets = (
        ('Estudiante y Materia', {
            'fields': ('student', 'subject'),
        }),
        ('Período', {
            'fields': ('quimestre', 'parcial', 'tipo_aporte'),
        }),
        ('Calificación', {
            'fields': ('calificacion', 'observaciones', 'registrado_por'),
        }),
        ('Fechas', {
            'fields': ('fecha_registro', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )

    def get_estudiante(self, obj):
        nombre = obj.student.usuario.nombre if obj.student and obj.student.usuario else '—'
        if obj.student:
            url = reverse('admin:students_student_change', args=[obj.student_id])
            return format_html('<a href="{}">{}</a>', url, nombre)
        return nombre
    get_estudiante.short_description = 'Estudiante'
    get_estudiante.admin_order_field = 'student__usuario__nombre'

    def get_nota_badge(self, obj):
        return nota_badge(obj.calificacion)
    get_nota_badge.short_description = 'Nota'
    get_nota_badge.admin_order_field = 'calificacion'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__usuario', 'subject', 'tipo_aporte', 'registrado_por__usuario',
        )

    actions = ['recalcular_promedios']

    @admin.action(description='♻️ Recalcular PromedioCache para seleccionados')
    def recalcular_promedios(self, request, queryset):
        try:
            from classes.models import PromedioCache
            students = set(queryset.values_list('student_id', flat=True))
            PromedioCache.objects.filter(student_id__in=students).delete()
            self.message_user(request, f'Cache limpiado para {len(students)} estudiante(s).')
        except Exception as e:
            self.message_user(request, f'Error: {e}', level=messages.ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
# ASISTENCIA
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display  = ['get_estudiante', 'get_clase', 'fecha', 'get_estado_badge', 'observacion']
    list_filter   = ['estado', 'fecha', 'inscripcion__clase__grade_level__ciclo',
                     'inscripcion__clase__subject']
    search_fields = ['inscripcion__estudiante__nombre', 'inscripcion__clase__name']
    autocomplete_fields = ['inscripcion']
    date_hierarchy = 'fecha'
    list_per_page  = 40

    def get_estudiante(self, obj):
        return obj.inscripcion.estudiante.nombre if obj.inscripcion and obj.inscripcion.estudiante else '—'
    get_estudiante.short_description = 'Estudiante'

    def get_clase(self, obj):
        return obj.inscripcion.clase.name if obj.inscripcion and obj.inscripcion.clase else '—'
    get_clase.short_description = 'Clase'

    def get_estado_badge(self, obj):
        palettes = {
            'Presente':    ('#166534', '#dcfce7'),
            'Ausente':     ('#991b1b', '#fee2e2'),
            'Justificado': ('#854d0e', '#fef9c3'),
        }
        color, bg = palettes.get(obj.estado, ('#374151', '#F3F4F6'))
        return estado_badge(obj.estado, color, bg)
    get_estado_badge.short_description = 'Estado'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'inscripcion__estudiante', 'inscripcion__clase__subject',
        )

    actions = ['marcar_presente', 'marcar_ausente', 'marcar_justificado']

    @admin.action(description='✅ Marcar como Presente')
    def marcar_presente(self, request, queryset):
        queryset.update(estado='Presente')

    @admin.action(description='❌ Marcar como Ausente')
    def marcar_ausente(self, request, queryset):
        queryset.update(estado='Ausente')

    @admin.action(description='📝 Marcar como Justificado')
    def marcar_justificado(self, request, queryset):
        queryset.update(estado='Justificado')


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY  (Registro de clase)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display  = ['get_estudiante', 'subject', 'get_clase', 'class_number',
                     'date', 'get_desempenio', 'get_docente']
    list_filter   = ['performance', 'subject', 'clase__grade_level__ciclo', 'date']
    search_fields = ['student__usuario__nombre', 'subject__name', 'clase__name',
                     'topics_worked', 'pieces']
    autocomplete_fields = ['student', 'clase', 'subject']
    readonly_fields   = ['created_at', 'updated_at', 'class_number']
    date_hierarchy    = 'date'
    list_per_page     = 25

    fieldsets = (
        ('Estudiante y clase', {
            'fields': ('student', 'clase', 'subject', 'date', 'class_number'),
        }),
        ('Contenido', {
            'fields': ('topics_worked', 'techniques', 'pieces', 'performance'),
        }),
        ('Evaluación', {
            'fields': ('strengths', 'areas_to_improve', 'homework', 'practice_time'),
        }),
        ('Observaciones', {
            'fields': ('observations',),
        }),
    )

    PERF_PALETTE = {
        'Excelente':        ('#166534', '#dcfce7'),
        'Muy Bueno':        ('#1e40af', '#dbeafe'),
        'Bueno':            ('#374151', '#f3f4f6'),
        'Regular':          ('#854d0e', '#fef9c3'),
        'Necesita mejorar': ('#991b1b', '#fee2e2'),
    }

    def get_estudiante(self, obj):
        return obj.student.usuario.nombre if obj.student and obj.student.usuario else '—'
    get_estudiante.short_description = 'Estudiante'

    def get_clase(self, obj):
        return obj.clase.name if obj.clase else '—'
    get_clase.short_description = 'Clase'

    def get_desempenio(self, obj):
        color, bg = self.PERF_PALETTE.get(obj.performance, ('#374151', '#f3f4f6'))
        return estado_badge(obj.performance, color, bg)
    get_desempenio.short_description = 'Desempeño'

    def get_docente(self, obj):
        docente = obj.get_teacher()
        return docente.nombre if docente else '—'
    get_docente.short_description = 'Docente'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__usuario', 'subject', 'clase',
        )


# ═══════════════════════════════════════════════════════════════════════════════
# DEBER  (Tarea asignada por docente)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Deber)
class DeberAdmin(admin.ModelAdmin):
    list_display  = ['titulo', 'get_clase', 'get_docente', 'fecha_entrega',
                     'get_estado_badge', 'get_progreso']
    list_filter   = ['estado', 'clase__grade_level__ciclo', 'clase__subject']
    search_fields = ['titulo', 'descripcion', 'teacher__nombre', 'clase__name']
    autocomplete_fields = ['clase', 'teacher']
    date_hierarchy    = 'fecha_entrega'
    readonly_fields   = ['fecha_asignacion']
    inlines           = [DeberEntregaInline]
    filter_horizontal = ['estudiantes_especificos']

    fieldsets = (
        ('Tarea', {
            'fields': ('titulo', 'descripcion', 'clase', 'teacher'),
        }),
        ('Configuración', {
            'fields': ('fecha_entrega', 'puntos_totales', 'estado', 'archivo_adjunto'),
        }),
        ('Asignación específica', {
            'fields': ('estudiantes_especificos',),
            'description': 'Si no se especifican estudiantes, aplica a toda la clase.',
            'classes': ('collapse',),
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion',),
            'classes': ('collapse',),
        }),
    )

    ESTADO_PALETTE = {
        'activo':   ('#166534', '#dcfce7'),
        'cerrado':  ('#374151', '#f3f4f6'),
        'borrador': ('#854d0e', '#fef9c3'),
    }

    def get_clase(self, obj):
        if not obj.clase:
            return '—'
        url = reverse('admin:classes_clase_change', args=[obj.clase_id])
        return format_html('<a href="{}">{}</a>', url, obj.clase.name)
    get_clase.short_description = 'Clase'

    def get_docente(self, obj):
        return obj.teacher.nombre if obj.teacher else '—'
    get_docente.short_description = 'Docente'

    def get_estado_badge(self, obj):
        color, bg = self.ESTADO_PALETTE.get(obj.estado, ('#374151', '#f3f4f6'))
        return estado_badge(obj.estado.title(), color, bg)
    get_estado_badge.short_description = 'Estado'

    def get_progreso(self, obj):
        pct = obj.porcentaje_entrega()
        color = '#DC2626' if pct < 30 else '#D97706' if pct < 70 else '#059669'
        return format_html(
            '<span style="color:{};font-weight:600;">{:.0f}%</span> '
            '<span style="color:#9CA3AF;font-size:11px">({} entregas)</span>',
            color, pct, obj.entregas_completadas(),
        )
    get_progreso.short_description = 'Progreso'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('clase__subject', 'teacher')


# ═══════════════════════════════════════════════════════════════════════════════
# DEBER ENTREGA
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(DeberEntrega)
class DeberEntregaAdmin(admin.ModelAdmin):
    list_display  = ['get_deber', 'get_estudiante', 'get_estado_badge',
                     'get_calificacion', 'fecha_entrega']
    list_filter   = ['estado', 'deber__clase__grade_level__ciclo']
    search_fields = ['deber__titulo', 'estudiante__nombre']
    autocomplete_fields = ['deber', 'estudiante']
    readonly_fields   = ['fecha_entrega', 'fecha_modificacion']

    ESTADO_PALETTE = {
        'pendiente':  ('#854d0e', '#fef9c3'),
        'entregado':  ('#1e40af', '#dbeafe'),
        'revisado':   ('#166534', '#dcfce7'),
        'tarde':      ('#991b1b', '#fee2e2'),
    }

    def get_deber(self, obj):
        url = reverse('admin:classes_deber_change', args=[obj.deber_id])
        return format_html('<a href="{}">{}</a>', url, obj.deber.titulo)
    get_deber.short_description = 'Deber'

    def get_estudiante(self, obj):
        return obj.estudiante.nombre if obj.estudiante else '—'
    get_estudiante.short_description = 'Estudiante'

    def get_estado_badge(self, obj):
        color, bg = self.ESTADO_PALETTE.get(obj.estado, ('#374151', '#f3f4f6'))
        return estado_badge(obj.get_estado_display(), color, bg)
    get_estado_badge.short_description = 'Estado'

    def get_calificacion(self, obj):
        return nota_badge(obj.calificacion) if obj.calificacion is not None else '—'
    get_calificacion.short_description = 'Calificación'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('deber__clase', 'estudiante')


# ═══════════════════════════════════════════════════════════════════════════════
# PROMEDIO CACHE  (solo lectura)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(PromedioCache)
class PromedioCacheAdmin(admin.ModelAdmin):
    list_display  = ['get_estudiante', 'subject', 'tipo_promedio', 'get_promedio', 'fecha_calculo']
    list_filter   = ['tipo_promedio', 'subject', 'student__grade_level__ciclo']
    search_fields = ['student__usuario__nombre', 'subject__name']
    readonly_fields = ['student', 'subject', 'parcial', 'quimestre',
                       'tipo_promedio', 'promedio', 'fecha_calculo']

    def has_add_permission(self, request):
        return False

    def get_estudiante(self, obj):
        return obj.student.usuario.nombre if obj.student and obj.student.usuario else '—'
    get_estudiante.short_description = 'Estudiante'

    def get_promedio(self, obj):
        return nota_badge(obj.promedio)
    get_promedio.short_description = 'Promedio'

    actions = ['limpiar_cache']

    @admin.action(description='🗑 Limpiar caché seleccionado')
    def limpiar_cache(self, request, queryset):
        n = queryset.count()
        queryset.delete()
        self.message_user(request, f'{n} entrada(s) de caché eliminadas.')
