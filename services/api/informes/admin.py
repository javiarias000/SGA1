from django.contrib import admin
from .models import (
    SesionClase, RecomendacionEstudiante,
    RegistroEnvioWhatsapp, SubmisionFormulario, ConfiguracionWhatsapp,
)


@admin.register(SesionClase)
class SesionClaseAdmin(admin.ModelAdmin):
    list_display = ['clase', 'fecha', 'tema', 'tab', 'col_index']
    list_filter = ['tab', 'fecha']
    search_fields = ['tema', 'descripcion', 'clase__name']


@admin.register(RecomendacionEstudiante)
class RecomendacionEstudianteAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'sesion', 'creado_en']
    search_fields = ['estudiante__nombre', 'recomendacion']


@admin.register(RegistroEnvioWhatsapp)
class RegistroEnvioWhatsappAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'materia', 'periodo', 'estado_wa', 'estado_form', 'enviado_en']
    list_filter = ['periodo', 'estado_wa', 'estado_form', 'ciclo_lectivo']
    search_fields = ['estudiante__usuario__nombre', 'telefono_usado']
    readonly_fields = ['enviado_en', 'actualizado_en']


@admin.register(SubmisionFormulario)
class SubmisionFormularioAdmin(admin.ModelAdmin):
    list_display = ['docente', 'materia', 'curso_nombre', 'exito', 'veces_enviado', 'enviado_en']
    list_filter = ['exito']
    search_fields = ['docente__nombre', 'curso_nombre']
    readonly_fields = ['enviado_en', 'ultimo_envio']


@admin.register(ConfiguracionWhatsapp)
class ConfiguracionWhatsappAdmin(admin.ModelAdmin):
    list_display = ['nombre_instancia', 'activa', 'ciclo_lectivo']
    list_filter = ['activa']
