from django.contrib import admin
from django.utils.html import format_html
from .models import ConfiguracionInstitucion


@admin.register(ConfiguracionInstitucion)
class ConfiguracionInstitucionAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'siglas', 'ciudad', 'anio_lectivo', 'email', 'wizard_link']
    fields        = ['nombre', 'siglas', 'ciudad', 'direccion', 'telefono',
                     'email', 'website', 'anio_lectivo', 'mision', 'vision']

    def has_add_permission(self, request):
        return not ConfiguracionInstitucion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def wizard_link(self, obj):
        return format_html('<a href="/setup/" class="button">⚙️ Abrir Wizard</a>')
    wizard_link.short_description = 'Configuración'
