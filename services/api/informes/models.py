from django.db import models
from django.utils import timezone


PERIODO_CHOICES = [
    ('1P', 'Primer Parcial'),
    ('2P', 'Segundo Parcial'),
    ('3P', 'Tercer Parcial'),
    ('4P', 'Cuarto Parcial'),
    ('1Q', 'Primer Quimestre'),
    ('2Q', 'Segundo Quimestre'),
    ('Anual', 'Anual'),
    ('A1', 'Asistencia Parcial 1'),
    ('A2', 'Asistencia Parcial 2'),
    ('A3', 'Asistencia Parcial 3'),
    ('A4', 'Asistencia Parcial 4'),
]


class SesionClase(models.Model):
    """Tema y descripción de una sesión de clase (columna en Google Sheets)."""

    clase = models.ForeignKey(
        'classes.Clase',
        on_delete=models.CASCADE,
        related_name='sesiones_informe',
        verbose_name='Clase',
    )
    fecha = models.DateField(default=timezone.now, verbose_name='Fecha')
    tema = models.CharField(max_length=500, blank=True, verbose_name='Tema')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    # Referencia al índice de columna en Google Sheets (para compatibilidad)
    sheet_id = models.CharField(max_length=200, blank=True, verbose_name='ID de Hoja')
    tab = models.CharField(max_length=100, blank=True, verbose_name='Pestaña')
    col_index = models.IntegerField(null=True, blank=True, verbose_name='Índice columna')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sesión de Clase'
        verbose_name_plural = 'Sesiones de Clase'
        unique_together = [('sheet_id', 'tab', 'col_index')]
        ordering = ['fecha', 'col_index']

    def __str__(self):
        return f"{self.clase} — {self.fecha} — {self.tema or f'Col {self.col_index}'}"


class RecomendacionEstudiante(models.Model):
    """Recomendación personalizada por alumno en una sesión de clase."""

    sesion = models.ForeignKey(
        SesionClase,
        on_delete=models.CASCADE,
        related_name='recomendaciones',
        verbose_name='Sesión',
    )
    estudiante = models.ForeignKey(
        'users.Usuario',
        on_delete=models.CASCADE,
        related_name='recomendaciones_clase',
        verbose_name='Estudiante',
    )
    recomendacion = models.TextField(verbose_name='Recomendación')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recomendación de Estudiante'
        verbose_name_plural = 'Recomendaciones de Estudiantes'
        unique_together = [('sesion', 'estudiante')]
        ordering = ['estudiante__nombre']

    def __str__(self):
        return f"{self.estudiante.nombre} — {self.sesion}"


class RegistroEnvioWhatsapp(models.Model):
    """Historial de mensajes WhatsApp enviados a representantes."""

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
    ]

    estudiante = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='envios_whatsapp',
        verbose_name='Estudiante',
    )
    materia = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='envios_whatsapp',
        verbose_name='Materia',
    )
    periodo = models.CharField(
        max_length=10,
        choices=PERIODO_CHOICES,
        verbose_name='Período',
    )
    ciclo_lectivo = models.CharField(max_length=20, default='2025-2026', verbose_name='Ciclo Lectivo')
    mensaje = models.TextField(verbose_name='Mensaje enviado')
    telefono_usado = models.CharField(max_length=30, blank=True, verbose_name='Teléfono')
    estado_wa = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado WhatsApp')
    estado_form = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado Formulario')
    error_wa = models.TextField(blank=True, verbose_name='Error WhatsApp')
    error_form = models.TextField(blank=True, verbose_name='Error Formulario')
    enviado_en = models.DateTimeField(auto_now_add=True, verbose_name='Enviado en')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Registro de Envío WhatsApp'
        verbose_name_plural = 'Registros de Envíos WhatsApp'
        ordering = ['-enviado_en']
        indexes = [
            models.Index(fields=['estudiante', 'periodo']),
            models.Index(fields=['estado_wa']),
            models.Index(fields=['-enviado_en']),
        ]

    def __str__(self):
        return f"{self.estudiante} — {self.periodo} — {self.estado_wa}"


class SubmisionFormulario(models.Model):
    """Historial de envíos al Google Form de informes docentes."""

    docente = models.ForeignKey(
        'users.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submisiones_form',
        verbose_name='Docente',
        limit_choices_to={'rol': 'DOCENTE'},
    )
    materia = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Materia',
    )
    curso_nombre = models.CharField(max_length=200, verbose_name='Curso')
    contenidos = models.TextField(blank=True, verbose_name='Contenidos trabajados')
    acciones = models.TextField(blank=True, verbose_name='Acciones correctivas')
    dificultades_json = models.JSONField(default=list, verbose_name='Estudiantes con dificultades')
    form_url = models.URLField(blank=True, verbose_name='URL del Formulario')
    form_fields_json = models.JSONField(default=list, verbose_name='Campos del formulario')
    exito = models.BooleanField(default=False, verbose_name='Éxito')
    error = models.TextField(blank=True, verbose_name='Error')
    veces_enviado = models.PositiveIntegerField(default=1, verbose_name='Veces enviado')
    enviado_en = models.DateTimeField(auto_now_add=True)
    ultimo_envio = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Submisión de Formulario'
        verbose_name_plural = 'Submisiones de Formularios'
        ordering = ['-enviado_en']

    def __str__(self):
        return f"{self.docente} — {self.materia} — {self.curso_nombre}"


class ConfiguracionWhatsapp(models.Model):
    """Configuración de instancia WhatsApp (Evolution API)."""

    nombre_instancia = models.CharField(max_length=100, unique=True, verbose_name='Nombre de instancia')
    activa = models.BooleanField(default=False, verbose_name='Activa')
    ciclo_lectivo = models.CharField(max_length=20, default='2025-2026', verbose_name='Ciclo Lectivo')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración WhatsApp'
        verbose_name_plural = 'Configuraciones WhatsApp'

    def __str__(self):
        return f"{self.nombre_instancia} ({'activa' if self.activa else 'inactiva'})"
