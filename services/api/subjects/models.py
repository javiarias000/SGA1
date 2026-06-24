from django.db import models

class Subject(models.Model):
    TIPO_MATERIA_CHOICES = [
        ('TEORIA', 'Teoría'),
        ('AGRUPACION', 'Agrupación'),
        ('INSTRUMENTO', 'Instrumento'),
        ('OTRO', 'Otro'), 
    ]

    name = models.CharField(max_length=120, unique=True, verbose_name="Nombre de la materia")
    description = models.TextField(blank=True, verbose_name="Descripción")
    tipo_materia = models.CharField(
        max_length=20,
        choices=TIPO_MATERIA_CHOICES,
        default='OTRO',
        verbose_name="Tipo de Materia"
    )

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        ordering = ['name']

    def __str__(self):
        return self.name