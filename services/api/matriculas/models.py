import uuid
from django.db import models
from django.conf import settings


class SolicitudDocente(models.Model):
    """Formulario público de auto-registro para docentes/personal."""

    class Estado(models.TextChoices):
        PENDIENTE  = 'PENDIENTE',  'Pendiente de revisión'
        APROBADO   = 'APROBADO',   'Aprobado — cuenta creada'
        RECHAZADO  = 'RECHAZADO',  'Rechazado'

    codigo_seguimiento = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)

    # Datos personales
    nombre_completo    = models.CharField(max_length=150)
    cedula             = models.CharField(max_length=20, blank=True)
    email              = models.EmailField(unique=True)
    telefono           = models.CharField(max_length=20, blank=True)
    especialidad       = models.CharField(max_length=120, blank=True)
    titulo_academico   = models.CharField(max_length=200, blank=True)
    experiencia_anios  = models.PositiveSmallIntegerField(null=True, blank=True,
                            verbose_name='Años de experiencia')
    mensaje            = models.TextField(blank=True,
                            verbose_name='Carta de presentación / mensaje adicional')

    # Admin
    notas_admin        = models.TextField(blank=True, verbose_name='Notas del administrador')
    username_generado  = models.CharField(max_length=60, blank=True, editable=False)
    password_temporal  = models.CharField(max_length=60, blank=True, editable=False,
                            help_text='Contraseña visible sólo justo después de aprobar.')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Solicitud de Registro — Docente'
        verbose_name_plural = 'Solicitudes de Registro — Docentes'

    def __str__(self):
        return f"{self.nombre_completo} ({self.email}) [{self.get_estado_display()}]"


class SolicitudMatricula(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de revisión'
        EN_REVISION = 'EN_REVISION', 'En revisión'
        NOVEDAD = 'NOVEDAD', 'Novedad — documentos a corregir'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    class TipoSolicitud(models.TextChoices):
        NUEVA = 'NUEVA', 'Inscripción nueva'
        RENOVACION = 'RENOVACION', 'Renovación de matrícula'

    # Identificador público para seguimiento sin cuenta
    codigo_seguimiento = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Tipo y estado
    tipo = models.CharField(max_length=12, choices=TipoSolicitud.choices, default=TipoSolicitud.NUEVA)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)

    # Vínculo opcional con usuario existente (renovaciones)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='solicitudes_matricula',
    )

    # Año solicitado (1–11)
    anio_solicitado = models.PositiveSmallIntegerField()

    # Instrumento (requerido solo en 1° año para estudiantes nuevos)
    instrumento_elegido = models.CharField(max_length=60, blank=True, default='')

    # Datos personales del aspirante
    nombre_completo = models.CharField(max_length=150)
    cedula = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField()

    # Datos del representante
    nombre_representante = models.CharField(max_length=150, blank=True, default='')
    email_representante = models.EmailField()
    phone_representante = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255, blank=True, default='')
    ciudad = models.CharField(max_length=80, blank=True, default='')

    # Ciclo lectivo (ej. "2025-2026")
    ciclo_lectivo = models.CharField(max_length=12)

    # Revisión IA
    revision_ia_completada = models.BooleanField(default=False)
    resumen_ia = models.TextField(blank=True, default='')
    tiene_novedades_ia = models.BooleanField(default=False)

    # Notas de secretaría
    notas_secretaria = models.TextField(blank=True, default='')
    secretaria = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='matriculas_revisadas',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Solicitud de Matrícula'
        verbose_name_plural = 'Solicitudes de Matrícula'

    def __str__(self):
        return f"{self.nombre_completo} — {self.anio_solicitado}° año ({self.ciclo_lectivo}) [{self.get_estado_display()}]"

    @property
    def edad(self):
        from datetime import date
        today = date.today()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )


class DocumentoMatricula(models.Model):
    class TipoDocumento(models.TextChoices):
        CEDULA = 'CEDULA', 'Copia de Cédula / Acta de Nacimiento'
        CERT_EDUCACION = 'CERT_EDUCACION', 'Certificado de Educación Regular'
        CERT_CONSERVATORIO = 'CERT_CONSERVATORIO', 'Certificado del Conservatorio'
        FOTO_CARNET = 'FOTO_CARNET', 'Foto Carnet'

    class EstadoIA(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de análisis'
        PROCESANDO = 'PROCESANDO', 'Procesando...'
        VALIDO = 'VALIDO', 'Válido'
        NOVEDAD = 'NOVEDAD', 'Con novedad'
        ERROR = 'ERROR', 'Error al procesar'

    solicitud = models.ForeignKey(
        SolicitudMatricula, on_delete=models.CASCADE, related_name='documentos'
    )
    tipo = models.CharField(max_length=25, choices=TipoDocumento.choices)
    archivo = models.FileField(upload_to='matriculas/documentos/%Y/%m/')
    nombre_original = models.CharField(max_length=255, blank=True)

    # Análisis IA
    estado_ia = models.CharField(max_length=12, choices=EstadoIA.choices, default=EstadoIA.PENDIENTE)
    observacion_ia = models.TextField(blank=True, default='')
    confianza_ia = models.FloatField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Documento de Matrícula'
        verbose_name_plural = 'Documentos de Matrícula'

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.solicitud.nombre_completo}"
