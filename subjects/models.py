from django.db import models

class Subject(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name="Nombre de la materia")
    description = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        ordering = ['name']

    def __str__(self):
        return self.name