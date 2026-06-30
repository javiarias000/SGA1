from django.db import models
from students.models import Student
from users.models import Usuario


class Instrumento(models.Model):
    class Tipo(models.TextChoices):
        CUERDA = 'CUERDA', 'Cuerda'
        VIENTO = 'VIENTO', 'Viento'
        PERCUSION = 'PERCUSION', 'Percusión'
        TECLADO = 'TECLADO', 'Teclado'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', 'Disponible'
        PRESTADO = 'PRESTADO', 'Prestado'
        MANTENIMIENTO = 'MANTENIMIENTO', 'En Mantenimiento'
        BAJA = 'BAJA', 'Baja'

    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.OTRO)
    marca = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, unique=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.DISPONIBLE)
    descripcion = models.TextField(blank=True)
    fecha_adquisicion = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Instrumento'
        verbose_name_plural = 'Instrumentos'
        ordering = ['tipo', 'nombre']

    def __str__(self):
        return f"{self.nombre} [{self.numero_serie}]"


class PrestamoInstrumento(models.Model):
    class EstadoPrestamo(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        DEVUELTO = 'DEVUELTO', 'Devuelto'
        VENCIDO = 'VENCIDO', 'Vencido'

    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE, related_name='prestamos')
    estudiante = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='prestamos_instrumentos')
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion_esperada = models.DateField()
    fecha_devolucion_real = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='prestamos_registrados')
    estado = models.CharField(max_length=10, choices=EstadoPrestamo.choices, default=EstadoPrestamo.ACTIVO)

    class Meta:
        verbose_name = 'Préstamo de Instrumento'
        verbose_name_plural = 'Préstamos de Instrumentos'
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f"{self.instrumento.nombre} → {self.estudiante.name}"
