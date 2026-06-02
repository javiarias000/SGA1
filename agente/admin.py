from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import AlertaEstudiante, InformeAsistido, ConfiguracionAgente


SEVER_PALETTE = {
    'BAJA':    ('#166534', '#dcfce7'),
    'MEDIA':   ('#854d0e', '#fef9c3'),
    'ALTA':    ('#9a3412', '#ffedd5'),
    'CRITICA': ('#991b1b', '#fee2e2'),
}
ESTADO_ALERTA_PALETTE = {
    'NUEVA':      ('#1e40af', '#dbeafe'),
    'VISTA':      ('#374151', '#f3f4f6'),
    'NOTIFICADA': ('#854d0e', '#fef9c3'),
    'RESUELTA':   ('#166534', '#dcfce7'),
}


@admin.register(AlertaEstudiante)
class AlertaEstudianteAdmin(admin.ModelAdmin):
    list_display  = ['get_estudiante', 'get_tipo_icon', 'get_severidad_badge',
                     'get_estado_badge', 'materia', 'get_dato_detectado',
                     'get_notif', 'created_at']
    list_filter   = ['severidad', 'tipo', 'estado', 'ciclo_lectivo',
                     'email_docente_enviado', 'email_representante_enviado']
    search_fields = ['estudiante__usuario__nombre', 'materia__name']
    autocomplete_fields = ['estudiante', 'materia']
    readonly_fields    = ['created_at', 'updated_at', 'fecha_notificacion']
    date_hierarchy     = 'created_at'
    list_per_page      = 25
    fieldsets = (
        ('Estudiante', {'fields': ('estudiante', 'materia', 'ciclo_lectivo')}),
        ('Alerta', {'fields': ('tipo', 'severidad', 'estado')}),
        ('Datos detectados', {'fields': ('promedio_detectado', 'porcentaje_inasistencia')}),
        ('Análisis IA', {'fields': ('analisis_ia', 'recomendaciones_ia')}),
        ('Mensajes generados', {'fields': ('mensaje_docente', 'mensaje_representante'), 'classes': ('collapse',)}),
        ('Notificaciones', {'fields': ('email_docente_enviado', 'email_representante_enviado', 'fecha_notificacion'), 'classes': ('collapse',)}),
        ('Fechas', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_estudiante(self, obj):
        if not (obj.estudiante and obj.estudiante.usuario):
            return '—'
        url = reverse('admin:students_student_change', args=[obj.estudiante_id])
        return format_html('<a href="{}">{}</a>', url, obj.estudiante.usuario.nombre)
    get_estudiante.short_description = 'Estudiante'

    def get_tipo_icon(self, obj):
        ICONS = {'CALIFICACION_BAJA': '📉', 'INASISTENCIA': '🚫',
                 'TENDENCIA_NEGATIVA': '⬇️', 'MULTIPLES_MATERIAS': '⚠️'}
        return format_html('{} {}', ICONS.get(obj.tipo, '❗'), obj.get_tipo_display())
    get_tipo_icon.short_description = 'Tipo'

    def get_severidad_badge(self, obj):
        c, bg = SEVER_PALETTE.get(obj.severidad, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;'
            'font-size:11px;font-weight:700;">{}</span>', bg, c, obj.severidad)
    get_severidad_badge.short_description = 'Severidad'
    get_severidad_badge.admin_order_field = 'severidad'

    def get_estado_badge(self, obj):
        c, bg = ESTADO_ALERTA_PALETTE.get(obj.estado, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;'
            'font-size:11px;">{}</span>', bg, c, obj.get_estado_display())
    get_estado_badge.short_description = 'Estado'

    def get_dato_detectado(self, obj):
        if obj.promedio_detectado is not None:
            from classes.admin import nota_badge
            return nota_badge(obj.promedio_detectado)
        if obj.porcentaje_inasistencia is not None:
            return format_html('<span style="color:#DC2626;font-weight:600">{}% ausencias</span>',
                               obj.porcentaje_inasistencia)
        return '—'
    get_dato_detectado.short_description = 'Dato'

    def get_notif(self, obj):
        d = '✅' if obj.email_docente_enviado else '⬜'
        r = '✅' if obj.email_representante_enviado else '⬜'
        return format_html('<span title="Docente">{}</span><span title="Representante">{}</span>', d, r)
    get_notif.short_description = '📧'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('estudiante__usuario', 'materia')

    actions = ['marcar_resuelta', 'marcar_vista']

    @admin.action(description='✅ Marcar como Resuelta')
    def marcar_resuelta(self, request, queryset):
        n = queryset.update(estado='RESUELTA')
        self.message_user(request, f'{n} alerta(s) resueltas.')

    @admin.action(description='👁 Marcar como Vista')
    def marcar_vista(self, request, queryset):
        n = queryset.update(estado='VISTA')
        self.message_user(request, f'{n} alerta(s) marcadas como vistas.')


@admin.register(InformeAsistido)
class InformeAsistidoAdmin(admin.ModelAdmin):
    list_display  = ['get_docente', 'get_estado_badge', 'get_activity', 'created_at']
    list_filter   = ['estado', 'created_at']
    search_fields = ['docente__nombre', 'texto_original']
    autocomplete_fields = ['docente', 'activity']
    readonly_fields    = ['created_at']
    fieldsets = (
        ('Docente', {'fields': ('docente', 'activity')}),
        ('Textos', {'fields': ('texto_original', 'texto_mejorado', 'sugerencias_ia')}),
        ('Estado', {'fields': ('estado', 'created_at')}),
    )

    ESTADO_PAL = {'BORRADOR': ('#854d0e', '#fef9c3'), 'ACEPTADO': ('#166534', '#dcfce7'),
                  'RECHAZADO': ('#991b1b', '#fee2e2')}

    def get_docente(self, obj):
        return obj.docente.nombre if obj.docente else '—'
    get_docente.short_description = 'Docente'

    def get_estado_badge(self, obj):
        c, bg = self.ESTADO_PAL.get(obj.estado, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;font-size:11px;">{}</span>',
            bg, c, obj.get_estado_display())
    get_estado_badge.short_description = 'Estado'

    def get_activity(self, obj):
        if not obj.activity:
            return '—'
        url = reverse('admin:classes_activity_change', args=[obj.activity_id])
        return format_html('<a href="{}">Actividad #{}</a>', url, obj.activity_id)
    get_activity.short_description = 'Actividad'


@admin.register(ConfiguracionAgente)
class ConfiguracionAgenteAdmin(admin.ModelAdmin):
    list_display  = ['ciclo_lectivo_activo', 'umbral_nota_alerta', 'umbral_inasistencia_pct',
                     'analisis_activo', 'notificar_docentes', 'notificar_representantes', 'updated_at']
    readonly_fields = ['updated_at']
    fieldsets = (
        ('Ciclo lectivo', {'fields': ('ciclo_lectivo_activo',)}),
        ('Umbrales de alerta', {
            'fields': ('umbral_nota_alerta', 'umbral_inasistencia_pct'),
            'description': 'Se genera alerta cuando la nota es menor al umbral o la inasistencia supera el porcentaje.',
        }),
        ('Activación y notificaciones', {'fields': ('analisis_activo', 'notificar_docentes', 'notificar_representantes')}),
        ('Meta', {'fields': ('updated_at',), 'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        return not ConfiguracionAgente.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
