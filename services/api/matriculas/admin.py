from django.contrib import admin
from django.utils.html import format_html
from .models import SolicitudMatricula, DocumentoMatricula, SolicitudDocente


class DocumentoMatriculaInline(admin.TabularInline):
    model = DocumentoMatricula
    extra = 0
    fields = ('tipo', 'archivo', 'get_estado_ia_display', 'observacion_ia', 'confianza_ia')
    readonly_fields = ('get_estado_ia_display', 'confianza_ia', 'uploaded_at')
    verbose_name = 'Documento'
    verbose_name_plural = '📄 Documentos adjuntos'

    def get_estado_ia_display(self, obj):
        PALETTE = {
            'VALIDO':     ('#166534', '#dcfce7'),
            'NOVEDAD':    ('#991b1b', '#fee2e2'),
            'PENDIENTE':  ('#854d0e', '#fef9c3'),
            'PROCESANDO': ('#1e40af', '#dbeafe'),
            'ERROR':      ('#374151', '#f3f4f6'),
        }
        c, bg = PALETTE.get(obj.estado_ia, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;font-size:11px;">{}</span>',
            bg, c, obj.get_estado_ia_display(),
        )
    get_estado_ia_display.short_description = 'Estado IA'


@admin.register(SolicitudMatricula)
class SolicitudMatriculaAdmin(admin.ModelAdmin):
    list_display  = ['get_nombre', 'anio_solicitado', 'instrumento_elegido',
                     'get_tipo_badge', 'get_estado_badge', 'ciclo_lectivo',
                     'get_ia_review', 'created_at']
    list_filter   = ['estado', 'tipo', 'anio_solicitado', 'ciclo_lectivo',
                     'revision_ia_completada', 'tiene_novedades_ia']
    search_fields = ['nombre_completo', 'cedula', 'codigo_seguimiento',
                     'email_representante', 'nombre_representante']
    readonly_fields = ['codigo_seguimiento', 'created_at', 'updated_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    inlines         = [DocumentoMatriculaInline]

    fieldsets = (
        ('Solicitud', {
            'fields': ('codigo_seguimiento', 'tipo', 'estado', 'ciclo_lectivo'),
        }),
        ('Datos del aspirante', {
            'fields': ('nombre_completo', 'cedula', 'fecha_nacimiento',
                       'anio_solicitado', 'instrumento_elegido'),
        }),
        ('Representante', {
            'fields': ('nombre_representante', 'email_representante',
                       'phone_representante', 'direccion', 'ciudad'),
        }),
        ('Revisión IA', {
            'fields': ('revision_ia_completada', 'tiene_novedades_ia', 'resumen_ia'),
            'classes': ('collapse',),
        }),
        ('Revisión secretaría', {
            'fields': ('notas_secretaria', 'secretaria'),
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    ESTADO_PALETTE = {
        'PENDIENTE':    ('#854d0e', '#fef9c3'),
        'EN_REVISION':  ('#1e40af', '#dbeafe'),
        'NOVEDAD':      ('#991b1b', '#fee2e2'),
        'APROBADA':     ('#166534', '#dcfce7'),
        'RECHAZADA':    ('#374151', '#f3f4f6'),
    }

    def get_nombre(self, obj):
        return format_html(
            '<strong>{}</strong><br>'
            '<span style="font-size:11px;color:#6B7280">CI: {}</span>',
            obj.nombre_completo, obj.cedula,
        )
    get_nombre.short_description = 'Aspirante'
    get_nombre.admin_order_field = 'nombre_completo'

    def get_tipo_badge(self, obj):
        color = '#1e40af' if obj.tipo == 'NUEVA' else '#6d28d9'
        bg    = '#dbeafe' if obj.tipo == 'NUEVA' else '#ede9fe'
        return format_html(
            '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, color, obj.get_tipo_display(),
        )
    get_tipo_badge.short_description = 'Tipo'

    def get_estado_badge(self, obj):
        c, bg = self.ESTADO_PALETTE.get(obj.estado, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, c, obj.get_estado_display(),
        )
    get_estado_badge.short_description = 'Estado'
    get_estado_badge.admin_order_field = 'estado'

    def get_ia_review(self, obj):
        if not obj.revision_ia_completada:
            return format_html('<span style="color:#9CA3AF">⏳ Pendiente</span>')
        if obj.tiene_novedades_ia:
            return format_html('<span style="color:#DC2626">⚠️ Con novedad</span>')
        return format_html('<span style="color:#059669">✅ OK</span>')
    get_ia_review.short_description = 'Revisión IA'

    actions = ['aprobar_y_crear_cuenta', 'rechazar', 'marcar_en_revision']

    @admin.action(description='✅ Aprobar y crear cuenta de estudiante')
    def aprobar_y_crear_cuenta(self, request, queryset):
        from .views import _crear_matricula_academica
        creadas = errores = 0
        for sol in queryset.exclude(estado='APROBADA'):
            try:
                _crear_matricula_academica(sol)
                sol.estado = 'APROBADA'
                sol.save(update_fields=['estado'])
                creadas += 1
            except Exception as e:
                self.message_user(request, f'Error en {sol.nombre_completo}: {e}',
                                  level='error')
                errores += 1
        if creadas:
            self.message_user(request,
                f'{creadas} solicitud(es) aprobada(s) — cuentas de estudiante creadas.')

    @admin.action(description='❌ Rechazar solicitudes seleccionadas')
    def rechazar(self, request, queryset):
        n = queryset.update(estado='RECHAZADA')
        self.message_user(request, f'{n} solicitud(es) rechazada(s).')

    @admin.action(description='🔍 Marcar en revisión')
    def marcar_en_revision(self, request, queryset):
        n = queryset.update(estado='EN_REVISION')
        self.message_user(request, f'{n} solicitud(es) en revisión.')


# ─── SOLICITUDES DOCENTE ─────────────────────────────────────────────────────

@admin.register(SolicitudDocente)
class SolicitudDocenteAdmin(admin.ModelAdmin):
    list_display  = ['get_nombre', 'especialidad', 'get_estado_badge',
                     'get_credenciales', 'created_at']
    list_filter   = ['estado', 'especialidad']
    search_fields = ['nombre_completo', 'cedula', 'email', 'especialidad']
    readonly_fields = ['codigo_seguimiento', 'username_generado', 'password_temporal',
                       'created_at', 'updated_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    actions = ['aprobar_y_crear_cuenta', 'rechazar']

    fieldsets = (
        ('Estado', {
            'fields': ('codigo_seguimiento', 'estado', 'notas_admin'),
        }),
        ('Datos personales', {
            'fields': ('nombre_completo', 'cedula', 'email', 'telefono'),
        }),
        ('Perfil profesional', {
            'fields': ('especialidad', 'titulo_academico', 'experiencia_anios', 'mensaje'),
        }),
        ('Credenciales generadas', {
            'fields': ('username_generado', 'password_temporal'),
            'description': 'La contraseña se muestra sólo una vez al aprobar.',
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    ESTADO_PALETTE = {
        'PENDIENTE': ('#854d0e', '#fef9c3'),
        'APROBADO':  ('#166534', '#dcfce7'),
        'RECHAZADO': ('#374151', '#f3f4f6'),
    }

    def get_nombre(self, obj):
        return format_html(
            '<strong>{}</strong><br>'
            '<span style="font-size:11px;color:#6B7280">{}</span>',
            obj.nombre_completo, obj.email,
        )
    get_nombre.short_description = 'Docente'
    get_nombre.admin_order_field = 'nombre_completo'

    def get_estado_badge(self, obj):
        c, bg = self.ESTADO_PALETTE.get(obj.estado, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, c, obj.get_estado_display(),
        )
    get_estado_badge.short_description = 'Estado'

    def get_credenciales(self, obj):
        if obj.username_generado:
            return format_html(
                '<code style="font-size:11px;">👤 {}</code>',
                obj.username_generado,
            )
        return format_html('<span style="color:#9CA3AF">—</span>')
    get_credenciales.short_description = 'Usuario asignado'

    @admin.action(description='✅ Aprobar y crear cuenta de docente')
    def aprobar_y_crear_cuenta(self, request, queryset):
        from .views import _crear_cuenta_docente
        for sol in queryset.filter(estado='PENDIENTE'):
            try:
                _, username, password = _crear_cuenta_docente(sol)
                self.message_user(
                    request,
                    f'✅ {sol.nombre_completo} — usuario: {username}  '
                    f'contraseña temporal: {password}',
                )
            except Exception as e:
                self.message_user(request, f'Error en {sol.nombre_completo}: {e}',
                                  level='error')

    @admin.action(description='❌ Rechazar solicitudes seleccionadas')
    def rechazar(self, request, queryset):
        n = queryset.update(estado='RECHAZADO')
        self.message_user(request, f'{n} solicitud(es) rechazada(s).')
