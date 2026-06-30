from django.db import models
from users.models import Usuario


class EventoCalendario(models.Model):
    class Tipo(models.TextChoices):
        FERIADO = 'FERIADO', 'Feriado'
        EXAMEN = 'EXAMEN', 'Examen / Evaluación'
        EVENTO = 'EVENTO', 'Evento'
        QUIMESTRE = 'QUIMESTRE', 'Inicio/Fin Quimestre'
        REUNION = 'REUNION', 'Reunión'

    class Visibilidad(models.TextChoices):
        ALL = 'ALL', 'Todos'
        DOCENTES = 'DOCENTES', 'Solo Docentes'
        ESTUDIANTES = 'ESTUDIANTES', 'Solo Estudiantes'

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.EVENTO)
    color = models.CharField(max_length=7, default='#4338ca')
    visible_para = models.CharField(max_length=15, choices=Visibilidad.choices, default=Visibilidad.ALL)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='eventos_creados')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento del Calendario'
        verbose_name_plural = 'Eventos del Calendario'
        ordering = ['fecha_inicio']

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio})"
