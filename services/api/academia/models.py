from django.db import models
from classes.models import GradeLevel, Subject
from users.models import Usuario # Assuming Usuario is in users.models

class Horario(models.Model):
    # Foreign Key relations
    curso = models.ForeignKey(GradeLevel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Curso")
    docente = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Docente")
    clase = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Clase / Asignatura")

    # Direct fields from JSON
    dia = models.CharField(max_length=20, verbose_name="Día")
    hora = models.CharField(max_length=50, verbose_name="Rango Horario")
    aula = models.CharField(max_length=100, blank=True, verbose_name="Aula")

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        unique_together = ('curso', 'dia', 'hora', 'clase', 'docente', 'aula') # Ensures uniqueness
        ordering = ['curso__level', 'curso__section', 'dia', 'hora']

    def __str__(self):
        return f"{self.curso} - {self.clase} ({self.dia} {self.hora})"