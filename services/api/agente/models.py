from django.db import models
from django.utils import timezone


class AlertaEstudiante(models.Model):
    """Alerta generada por el agente IA sobre el rendimiento de un estudiante."""

    class TipoAlerta(models.TextChoices):
        CALIFICACION_BAJA = 'CALIFICACION_BAJA', 'Calificación baja'
        INASISTENCIA = 'INASISTENCIA', 'Alta inasistencia'
        TENDENCIA_NEGATIVA = 'TENDENCIA_NEGATIVA', 'Tendencia negativa'
        MULTIPLES_MATERIAS = 'MULTIPLES_MATERIAS', 'Bajo rendimiento en múltiples materias'

    class Severidad(models.TextChoices):
        BAJA = 'BAJA', 'Baja'
        MEDIA = 'MEDIA', 'Media'
        ALTA = 'ALTA', 'Alta'
        CRITICA = 'CRITICA', 'Crítica'

    class Estado(models.TextChoices):
        NUEVA = 'NUEVA', 'Nueva'
        VISTA = 'VISTA', 'Vista por docente'
        NOTIFICADA = 'NOTIFICADA', 'Notificado representante'
        RESUELTA = 'RESUELTA', 'Resuelta'

    estudiante = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='alertas_ia'
    )
    tipo = models.CharField(max_length=30, choices=TipoAlerta.choices)
    severidad = models.CharField(max_length=10, choices=Severidad.choices, default=Severidad.MEDIA)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.NUEVA)

    # Datos del análisis
    materia = models.ForeignKey(
        'subjects.Subject', on_delete=models.SET_NULL, null=True, blank=True
    )
    promedio_detectado = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    porcentaje_inasistencia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Texto generado por la IA
    analisis_ia = models.TextField(help_text='Análisis detallado generado por el agente')
    recomendaciones_ia = models.TextField(blank=True)
    mensaje_docente = models.TextField(blank=True, help_text='Mensaje sugerido para el docente')
    mensaje_representante = models.TextField(blank=True, help_text='Mensaje sugerido para el representante')

    # Notificaciones
    email_docente_enviado = models.BooleanField(default=False)
    email_representante_enviado = models.BooleanField(default=False)
    fecha_notificacion = models.DateTimeField(null=True, blank=True)

    # Ciclo lectivo al que pertenece el análisis
    ciclo_lectivo = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-severidad', '-created_at']
        verbose_name = 'Alerta de Estudiante'
        verbose_name_plural = 'Alertas de Estudiantes'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.estudiante} [{self.severidad}]'


class InformeAsistido(models.Model):
    """Informe de clase mejorado por el agente IA."""

    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador IA'
        ACEPTADO = 'ACEPTADO', 'Aceptado por docente'
        RECHAZADO = 'RECHAZADO', 'Rechazado'

    # Puede estar vinculado a un Activity existente o ser independiente
    activity = models.OneToOneField(
        'classes.Activity', on_delete=models.CASCADE,
        null=True, blank=True, related_name='informe_asistido'
    )
    docente = models.ForeignKey(
        'users.Usuario', on_delete=models.CASCADE, related_name='informes_asistidos'
    )

    # Texto original del docente
    texto_original = models.TextField()

    # Texto mejorado por IA
    texto_mejorado = models.TextField()
    sugerencias_ia = models.TextField(blank=True, help_text='Lista de mejoras realizadas')

    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Informe Asistido por IA'
        verbose_name_plural = 'Informes Asistidos por IA'

    def __str__(self):
        return f'Informe de {self.docente} — {self.created_at.date()}'


class ConfiguracionAgente(models.Model):
    """Configuración global del agente IA (singleton)."""

    umbral_nota_alerta = models.DecimalField(
        max_digits=4, decimal_places=2, default=6.00,
        help_text='Nota por debajo de la cual se genera alerta (ej: 6.00)'
    )
    umbral_inasistencia_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00,
        help_text='Porcentaje de inasistencias para generar alerta (ej: 20.00)'
    )
    analisis_activo = models.BooleanField(default=True)
    notificar_docentes = models.BooleanField(default=True)
    notificar_representantes = models.BooleanField(default=True)
    ciclo_lectivo_activo = models.CharField(max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración del Agente'

    def __str__(self):
        return f'Configuración Agente (umbral nota: {self.umbral_nota_alerta})'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
