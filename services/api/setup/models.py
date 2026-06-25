from django.db import models


class ConfiguracionInstitucion(models.Model):
    nombre = models.CharField(max_length=200, default='', verbose_name='Nombre de la institución')
    siglas = models.CharField(max_length=20, blank=True, verbose_name='Siglas')
    ciudad = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    direccion = models.CharField(max_length=300, blank=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, verbose_name='Email institucional')
    website = models.URLField(blank=True, verbose_name='Sitio web')
    anio_lectivo = models.CharField(max_length=20, default='2025-2026', verbose_name='Año lectivo actual')
    mision = models.TextField(blank=True, verbose_name='Misión')
    vision = models.TextField(blank=True, verbose_name='Visión')

    class Meta:
        verbose_name = 'Configuración de la Institución'

    def __str__(self):
        return self.nombre or 'Institución sin nombre'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
