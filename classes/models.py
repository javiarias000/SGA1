from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from students.models import Student
from django.db.models.signals import post_save, post_delete
from decimal import Decimal
from datetime import timezone, time
from subjects.models import Subject
from teachers.models import Teacher
from users.models import Usuario


class GradeLevel(models.Model):
    """Modelo para Grado y Paralelo"""
    LEVEL_CHOICES = [
        ('1', 'Primero'),
        ('2', 'Segundo'),
        ('3', 'Tercero'),
        ('4', 'Cuarto'),
        ('5', 'Quinto'),
        ('6', 'Sexto'),
        ('7', 'Séptimo'),
        ('8', 'Octavo'),
        ('9', 'Noveno'),
        ('10', 'Décimo'),
        ('11', 'Onceavo'),
    ]

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        verbose_name="Nivel"
    )
    section = models.CharField(
        max_length=100,
        verbose_name="Paralelo/Sección"
    )

    class Meta:
        unique_together = ('level', 'section')
        verbose_name = "Grado"
        verbose_name_plural = "Grados"
        ordering = ['level', 'section']

    def __str__(self):
        return f"{self.get_level_display()} '{self.section}'"


class Clase(models.Model):
    """Instancia académica de una materia en un ciclo lectivo.

    Regla de negocio:
    - Teoría/Agrupación: normalmente 1 clase por materia + ciclo + paralelo (o grado/paralelo).
    - Instrumento: 1 clase por materia + ciclo + docente_base.
    """

    name = models.CharField(max_length=200, verbose_name="Nombre de la clase")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='clases', verbose_name="Materia", null=True)

    ciclo_lectivo = models.CharField(max_length=20, default='2025-2026', verbose_name='Ciclo lectivo')
    paralelo = models.CharField(max_length=100, blank=True, default='', verbose_name='Paralelo')

    # Responsable base (principalmente para Instrumento)
    docente_base = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clases_como_docente_base',
        verbose_name='Docente base'
    )

    description = models.TextField(blank=True, verbose_name="Descripción")
    schedule = models.CharField(max_length=200, blank=True, verbose_name="Horario")
    room = models.CharField(max_length=100, blank=True, verbose_name="Aula/Salón")
    max_students = models.PositiveIntegerField(default=30, verbose_name="Capacidad máxima")
    active = models.BooleanField(default=True, verbose_name="Activa")
    fecha = models.DateField(verbose_name="Fecha", null=True, blank=True)
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.SET_NULL, related_name='clases', verbose_name="Nivel/Paralelo", null=True, blank=True)
    periodo = models.CharField(max_length=100, blank=True, verbose_name="Período Académico")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Clase"
        verbose_name_plural = "Clases"
        ordering = ['subject', 'name']
        constraints = [
            # Teoría/Agrupación: subject + ciclo + paralelo
            models.UniqueConstraint(
                fields=['subject', 'ciclo_lectivo', 'paralelo'],
                condition=models.Q(docente_base__isnull=True),
                name='uniq_clase_subject_ciclo_paralelo_when_no_docente_base'
            ),
            # Instrumento: subject + ciclo + docente_base
            models.UniqueConstraint(
                fields=['subject', 'ciclo_lectivo', 'docente_base'],
                condition=models.Q(docente_base__isnull=False),
                name='uniq_clase_subject_ciclo_docente_base_when_docente_base'
            ),
        ]

    def __str__(self):
        return f"{self.subject} - {self.name}"

    def get_enrolled_count(self):
        return self.enrollments.filter(estado='ACTIVO').count()

    def has_space(self):
        return self.get_enrolled_count() < self.max_students


class Enrollment(models.Model):
    """Inscripción Estudiante–Clase–Docente."""

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        RETIRADO = 'RETIRADO', 'Retirado'

    estudiante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='enrollments_as_student',
        verbose_name='Estudiante'
    )
    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Clase'
    )
    docente = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollments_as_teacher',
        verbose_name='Docente asignado'
    )

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    date_enrolled = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'clase')
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def __str__(self):
        return f"{self.estudiante.nombre} en {self.clase.name}"


class Horario(models.Model):
    """Modelo para horarios de clases"""
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='horarios', verbose_name="Clase")
    dia_semana = models.CharField(max_length=20, choices=[
        ('Lunes', 'Lunes'), ('Martes', 'Martes'), ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'), ('Viernes', 'Viernes'), ('Sábado', 'Sábado'),
        ('Domingo', 'Domingo')
    ], verbose_name="Día de la Semana")
    hora_inicio = models.TimeField(verbose_name="Hora de Inicio")
    hora_fin = models.TimeField(verbose_name="Hora de Fin")

    class Meta:
        unique_together = ('clase', 'dia_semana', 'hora_inicio')
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.clase.name} - {self.get_dia_semana_display()} ({self.hora_inicio}-{self.hora_fin})"


class Activity(models.Model):
    """Modelo de Actividad/Clase"""

    PERFORMANCE_CHOICES = [
        ('Excelente', 'Excelente'),
        ('Muy Bueno', 'Muy Bueno'),
        ('Bueno', 'Bueno'),
        ('Regular', 'Regular'),
        ('Necesita mejorar', 'Necesita mejorar'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='activities', verbose_name="Estudiante")
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='activities')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='activities', verbose_name="Materia", null=True)
    class_number = models.PositiveIntegerField(verbose_name="Número de clase")
    date = models.DateField(verbose_name="Fecha de clase")
    
    topics_worked = models.TextField(blank=True, verbose_name="Temas trabajados")
    techniques = models.TextField(blank=True, verbose_name="Técnicas desarrolladas")
    pieces = models.CharField(max_length=500, blank=True, verbose_name="Piezas/Repertorio")
    
    performance = models.CharField(max_length=50, choices=PERFORMANCE_CHOICES, default='Bueno', verbose_name="Desempeño")
    strengths = models.TextField(blank=True, verbose_name="Fortalezas")
    areas_to_improve = models.TextField(blank=True, verbose_name="Áreas a mejorar")
    
    homework = models.TextField(blank=True, verbose_name="Tareas para casa")
    practice_time = models.PositiveIntegerField(
        default=30, 
        validators=[MinValueValidator(15), MaxValueValidator(180)],
        verbose_name="Tiempo de práctica (minutos)"
    )
    
    observations = models.TextField(blank=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-class_number']
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        unique_together = ['student', 'subject', 'class_number']
    
    def __str__(self):
        return f"{self.student.name} - {self.subject} - Clase #{self.class_number}"
    
    def save(self, *args, **kwargs):
        if not self.class_number:
            last_class = Activity.objects.filter(
                student=self.student,
                subject=self.subject
            ).order_by('-class_number').first()
            
            self.class_number = (last_class.class_number + 1) if last_class else 1
        
        super().save(*args, **kwargs)
    
    def get_teacher(self):
        # Obtener docente desde la inscripción del estudiante en la clase
        if not self.student.usuario:
            return None
        enrollment = self.clase.enrollments.filter(estudiante=self.student.usuario, estado='ACTIVO').first()
        if enrollment and enrollment.docente:
            return enrollment.docente
        return None


# ============================================
# LEGACY (compatibilidad)
# ============================================


class Grade(models.Model):
    """Modelo legacy de calificaciones (compatibilidad con vistas/templates antiguas).

    Nota: El sistema nuevo usa Calificacion (por Enrollment) y/o CalificacionParcial.
    """

    PERIOD_CHOICES = [
        ('Primer Parcial', 'Primer Parcial'),
        ('Segundo Parcial', 'Segundo Parcial'),
        ('Tercer Parcial', 'Tercer Parcial'),
        ('Examen Final', 'Examen Final'),
        ('Quimestre 1', 'Quimestre 1'),
        ('Quimestre 2', 'Quimestre 2'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='grades', verbose_name='Estudiante')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades', verbose_name='Materia', null=True)

    period = models.CharField(max_length=50, choices=PERIOD_CHOICES, verbose_name='Período')
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name='Calificación'
    )
    comments = models.TextField(blank=True, verbose_name='Comentarios')
    date = models.DateField(verbose_name='Fecha de calificación')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        ordering = ['-date']
        unique_together = [('student', 'subject', 'period')]

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.period}: {self.score}"


class Attendance(models.Model):
    """Modelo legacy de asistencia (compatibilidad con vistas/templates antiguas).

    Nota: El sistema nuevo usa Asistencia (por Enrollment).
    """

    STATUS_CHOICES = [
        ('Presente', '✅ Presente'),
        ('Ausente', '❌ Ausente'),
        ('Tardanza', '⏰ Tardanza'),
        ('Justificado', '📝 Justificado'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendances', verbose_name='Estudiante')
    date = models.DateField(verbose_name='Fecha')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Presente', verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-date']
        unique_together = [('student', 'date')]

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"


# ============================================
# SISTEMA NUEVO (Enrollment-based)
# ============================================


class Calificacion(models.Model):
    """Calificaciones por inscripción (permite múltiples notas por estudiante en una misma clase)."""

    inscripcion = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='calificaciones')
    descripcion = models.CharField(max_length=200)
    nota = models.DecimalField(max_digits=5, decimal_places=2)
    fecha = models.DateField()

    class Meta:
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        ordering = ['-fecha', 'id']

    def __str__(self):
        return f"{self.inscripcion.estudiante.nombre} - {self.descripcion}: {self.nota}"


class Asistencia(models.Model):
    """Asistencia por inscripción."""

    class Estado(models.TextChoices):
        PRESENTE = 'Presente', 'Presente'
        AUSENTE = 'Ausente', 'Ausente'
        JUSTIFICADO = 'Justificado', 'Justificado'

    inscripcion = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices)
    observacion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-fecha', 'id']
        unique_together = [('inscripcion', 'fecha')]

    def __str__(self):
        return f"{self.inscripcion.estudiante.nombre} - {self.fecha} - {self.estado}"





# ============================================
# SISTEMA UNIFICADO DE CALIFICACIONES
# ============================================

class TipoAporte(models.Model):
    """
    Tipos de aportes para calificaciones
    Ejemplos: Trabajo en clase, Exposición, Transcripción, Deberes, etc.
    """
    nombre = models.CharField(max_length=100, verbose_name="Nombre del aporte")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    peso = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.0, 
        verbose_name="Peso en el promedio",
        help_text="Peso relativo de este aporte en el cálculo del promedio"
    )
    orden = models.IntegerField(default=0, verbose_name="Orden de visualización")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tipo de Aporte"
        verbose_name_plural = "Tipos de Aportes"
        ordering = ['orden', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} (Peso: {self.peso})"


class CalificacionParcial(models.Model):
    """
    MODELO CENTRAL UNIFICADO DE CALIFICACIONES
    Maneja todas las calificaciones por parcial, tipo de aporte y quimestre
    """
    PARCIAL_CHOICES = [
        ('1P', 'Primer Parcial'),
        ('2P', 'Segundo Parcial'),
        ('3P', 'Tercer Parcial'),
        ('4P', 'Cuarto Parcial'),  # Ahora con 4 parciales
    ]
    
    QUIMESTRE_CHOICES = [
        ('Q1', 'Primer Quimestre'),
        ('Q2', 'Segundo Quimestre'),
    ]
    
    # Relaciones principales
    student = models.ForeignKey(
        'students.Student', 
        on_delete=models.CASCADE, 
        related_name='calificaciones_parciales',
        verbose_name="Estudiante"
    )
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='calificaciones_parciales', verbose_name="Materia", null=True)
    
    parcial = models.CharField(
        max_length=2, 
        choices=PARCIAL_CHOICES,
        verbose_name="Parcial"
    )
    
    quimestre = models.CharField(
        max_length=2,
        choices=QUIMESTRE_CHOICES, # Corrected typo here
        default='Q1',
        verbose_name="Quimestre"
    )
    
    tipo_aporte = models.ForeignKey(
        TipoAporte, 
        on_delete=models.PROTECT,
        verbose_name="Tipo de Aporte",
        related_name="calificaciones"
    )
    
    # Calificación (0-10)
    calificacion = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        default=0,
        verbose_name="Calificación",
        help_text="Nota sobre 10"
    )
    
    # Metadata
    fecha_registro = models.DateField(
        auto_now_add=True, 
        verbose_name="Fecha de Registro"
    )
    fecha_actualizacion = models.DateField(
        auto_now=True, 
        verbose_name="Última Actualización"
    )
    observaciones = models.TextField(
        blank=True, 
        verbose_name="Observaciones"
    )
    registrado_por = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Registrado por"
    )
    
    class Meta:
        verbose_name = "Calificación Parcial"
        verbose_name_plural = "Calificaciones Parciales"
        unique_together = ['student', 'subject', 'parcial', 'quimestre', 'tipo_aporte']
        ordering = ['-fecha_actualizacion', 'student__usuario__nombre']
        indexes = [
            models.Index(fields=['student', 'subject', 'parcial']),
            models.Index(fields=['student', 'quimestre']),
            models.Index(fields=['parcial', 'quimestre']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.subject} - {self.get_parcial_display()} - {self.tipo_aporte.nombre}: {self.calificacion}"
    
    def get_escala_cualitativa(self):
        """
        Obtiene la escala cualitativa según el Ministerio de Educación Ecuador
        DAR: Domina los Aprendizajes Requeridos (9-10)
        AAR: Alcanza los Aprendizajes Requeridos (7-8.99)
        PAAR: Próximo a Alcanzar los Aprendizajes (4.01-6.99)
        NAAR: No Alcanza los Aprendizajes Requeridos (≤4)
        """
        nota = float(self.calificacion)
        if nota >= 9:
            return {
                'codigo': 'DAR', 
                'nombre': 'Domina los Aprendizajes Requeridos', 
                'color': '#10B981',
                'text_color': '#FFFFFF'
            }
        elif nota >= 7:
            return {
                'codigo': 'AAR', 
                'nombre': 'Alcanza los Aprendizajes Requeridos', 
                'color': '#3B82F6',
                'text_color': '#FFFFFF'
            }
        elif nota >= 4.01:
            return {
                'codigo': 'PAAR', 
                'nombre': 'Próximo a Alcanzar los Aprendizajes', 
                'color': '#F59E0B',
                'text_color': '#000000'
            }
        else:
            return {
                'codigo': 'NAAR', 
                'nombre': 'No Alcanza los Aprendizajes Requeridos', 
                'color': '#EF4444',
                'text_color': '#FFFFFF'
            }
    
    @staticmethod
    def calcular_promedio_parcial(student, subject, parcial, quimestre='Q1'):
        """
        Calcula el promedio ponderado de un parcial específico
        """
        calificaciones = CalificacionParcial.objects.filter(
            student=student,
            subject=subject,
            parcial=parcial,
            quimestre=quimestre,
            calificacion__gt=0
        ).select_related('tipo_aporte')
        
        if not calificaciones.exists():
            return Decimal('0.00')
        
        # Promedio ponderado según peso de cada aporte
        suma_ponderada = sum(
            c.calificacion * c.tipo_aporte.peso 
            for c in calificaciones
        )
        suma_pesos = sum(c.tipo_aporte.peso for c in calificaciones)
        
        if suma_pesos == 0:
            return Decimal('0.00')
        
        promedio = suma_ponderada / suma_pesos
        return round(promedio, 2)
    
    @staticmethod
    def calcular_promedio_quimestre(student, subject, quimestre='Q1'):
        """
        Calcula el promedio de quimestre (promedio de todos los parciales)
        Con 4 parciales ahora
        """
        promedios = []
        
        for parcial, _ in CalificacionParcial.PARCIAL_CHOICES:
            prom = CalificacionParcial.calcular_promedio_parcial(
                student, subject, parcial, quimestre
            )
            if prom > 0:
                promedios.append(float(prom))
        
        if not promedios:
            return Decimal('0.00')
        
        promedio_quimestre = sum(promedios) / len(promedios)
        return Decimal(str(round(promedio_quimestre, 2)))
    
    @staticmethod
    def calcular_nota_final_materia(student, subject):
        """
        Calcula la nota final de una materia
        Fórmula: (Q1_80% + Q2_80%) + Examen_Final_20%
        Por ahora solo calcula el promedio de quimestres (80%)
        """
        prom_q1 = CalificacionParcial.calcular_promedio_quimestre(student, subject, 'Q1')
        prom_q2 = CalificacionParcial.calcular_promedio_quimestre(student, subject, 'Q2')
        
        # Equivalencia 80% (0.8 de cada quimestre)
        equivalencia_q1 = float(prom_q1) * 0.4  # 40% del total
        equivalencia_q2 = float(prom_q2) * 0.4  # 40% del total
        
        # Total 80% (falta el 20% del examen final)
        total_80_porciento = equivalencia_q1 + equivalencia_q2
        
        return Decimal(str(round(total_80_porciento, 2)))
    
    @staticmethod
    def calcular_promedio_general(student):
        """
        Calcula el promedio general del estudiante (todas las materias)
        """
        materias = CalificacionParcial.objects.filter(
            student=student
        ).values_list('subject', flat=True).distinct()
        
        if not materias:
            return Decimal('0.00')
        
        promedios = []
        for materia in materias:
            prom_q1 = CalificacionParcial.calcular_promedio_quimestre(student, materia, 'Q1')
            prom_q2 = CalificacionParcial.calcular_promedio_quimestre(student, materia, 'Q2')
            
            # Promedio de ambos quimestres
            if prom_q1 > 0 and prom_q2 > 0:
                promedio_materia = (float(prom_q1) + float(prom_q2)) / 2
                promedios.append(promedio_materia)
            elif prom_q1 > 0:
                promedios.append(float(prom_q1))
            elif prom_q2 > 0:
                promedios.append(float(prom_q2))
        
        if not promedios:
            return Decimal('0.00')
        
        promedio_general = sum(promedios) / len(promedios)
        return Decimal(str(round(promedio_general, 2)))
    
    @staticmethod
    def obtener_libreta_completa(student):
        """
        Genera la libreta completa del estudiante con todas las calificaciones
        Similar al formato del Excel que proporcionaste
        """
        materias = CalificacionParcial.objects.filter(
            student=student
        ).values_list('subject', flat=True).distinct()
        
        libreta = {
            'estudiante': {
                'nombre': student.name,
                'id': student.id,
            },
            'materias': [],
            'promedio_general': float(CalificacionParcial.calcular_promedio_general(student))
        }
        
        for materia in materias:
            materia_data = {
                'nombre': materia,
                'quimestre1': {
                    'parciales': {},
                    'promedio': float(CalificacionParcial.calcular_promedio_quimestre(student, materia, 'Q1'))
                },
                'quimestre2': {
                    'parciales': {},
                    'promedio': float(CalificacionParcial.calcular_promedio_quimestre(student, materia, 'Q2'))
                },
                'nota_final': float(CalificacionParcial.calcular_nota_final_materia(student, materia))
            }
            
            # Obtener calificaciones de cada parcial
            for parcial, parcial_nombre in CalificacionParcial.PARCIAL_CHOICES:
                # Q1
                califs_q1 = CalificacionParcial.objects.filter(
                    student=student,
                    subject=materia,
                    parcial=parcial,
                    quimestre='Q1'
                ).select_related('tipo_aporte')
                
                materia_data['quimestre1']['parciales'][parcial] = {
                    'nombre': parcial_nombre,
                    'aportes': [
                        {
                            'tipo': c.tipo_aporte.nombre,
                            'nota': float(c.calificacion)
                        } for c in califs_q1
                    ],
                    'promedio': float(CalificacionParcial.calcular_promedio_parcial(student, materia, parcial, 'Q1'))
                }
                
                # Q2
                califs_q2 = CalificacionParcial.objects.filter(
                    student=student,
                    subject=materia,
                    parcial=parcial,
                    quimestre='Q2'
                ).select_related('tipo_aporte')
                
                materia_data['quimestre2']['parciales'][parcial] = {
                    'nombre': parcial_nombre,
                    'aportes': [
                        {
                            'tipo': c.tipo_aporte.nombre,
                            'nota': float(c.calificacion)
                        } for c in califs_q2
                    ],
                    'promedio': float(CalificacionParcial.calcular_promedio_parcial(student, materia, parcial, 'Q2'))
                }
            
            libreta['materias'].append(materia_data)
        
        return libreta

    @staticmethod
    def obtener_resumen_estudiante(student):
        """
        Devuelve un resumen compacto para emails:
        {
          'promedio_general': float,
          'materias': [
             {
               'nombre': subject,
               'parciales': {'1P': float, '2P': float, '3P': float, '4P': float},
               'promedio_final': float
             }
          ]
        }
        """
        materias = CalificacionParcial.objects.filter(
            student=student
        ).values_list('subject', flat=True).distinct()

        resumen = {
            'promedio_general': float(CalificacionParcial.calcular_promedio_general(student)),
            'materias': []
        }
        for materia in materias:
            parciales = {}
            for parcial, _ in CalificacionParcial.PARCIAL_CHOICES:
                parciales[parcial] = float(
                    CalificacionParcial.calcular_promedio_parcial(student, materia, parcial)
                )
            promedio_final = float(
                CalificacionParcial.calcular_nota_final_materia(student, materia)
            )
            resumen['materias'].append({
                'nombre': materia,
                'parciales': parciales,
                'promedio_final': promedio_final
            })
        return resumen


class PromedioCache(models.Model):
    """
    Cache para optimizar cálculos de promedios frecuentes
    Se actualiza automáticamente mediante signals
    """
    TIPO_CHOICES = [
        ('parcial', 'Parcial'),
        ('quimestre', 'Quimestre'),
        ('general', 'General'),
    ]
    
    student = models.ForeignKey(
        'students.Student', 
        on_delete=models.CASCADE,
        related_name='cache_promedios'
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='cache_promedios', verbose_name="Materia", blank=True, null=True)
    parcial = models.CharField(max_length=2, blank=True)
    quimestre = models.CharField(max_length=2, blank=True)
    tipo_promedio = models.CharField(max_length=20, choices=TIPO_CHOICES)
    promedio = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fecha_calculo = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Promedio (Cache)"
        verbose_name_plural = "Promedios (Cache)"
        unique_together = ['student', 'subject', 'parcial', 'quimestre', 'tipo_promedio']
        indexes = [
            models.Index(fields=['student', 'tipo_promedio']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.tipo_promedio}: {self.promedio}"

# ============================================
# SIGNALS PARA ACTUALIZACIÓN AUTOMÁTICA
# ============================================

@receiver([post_save, post_delete], sender=CalificacionParcial)
def actualizar_cache_promedios(sender, instance, **kwargs):
    """
    Actualiza automáticamente el cache de promedios cuando se guardan
    o eliminan calificaciones
    """
    try:
        # 1. Actualizar promedio del parcial específico
        promedio_parcial = CalificacionParcial.calcular_promedio_parcial(
            instance.student, 
            instance.subject, 
            instance.parcial,
            instance.quimestre
        )
        PromedioCache.objects.update_or_create(
            student=instance.student,
            subject=instance.subject,
            parcial=instance.parcial,
            quimestre=instance.quimestre,
            tipo_promedio='parcial',
            defaults={'promedio': promedio_parcial}
        )
        
        # 2. Actualizar promedio del quimestre
        promedio_quimestre = CalificacionParcial.calcular_promedio_quimestre(
            instance.student, 
            instance.subject, 
            instance.quimestre
        )
        PromedioCache.objects.update_or_create(
            student=instance.student,
            subject=instance.subject,
            quimestre=instance.quimestre,
            tipo_promedio='quimestre',
            defaults={'promedio': promedio_quimestre}
        )
        
        # 3. Actualizar promedio general del estudiante
        promedio_general = CalificacionParcial.calcular_promedio_general(instance.student)
        PromedioCache.objects.update_or_create(
            student=instance.student,
            subject=None, # Set subject to None for general average
            tipo_promedio='general',
            defaults={'promedio': promedio_general}
        )
        
    except Exception as e:
        # Log del error pero no interrumpir el guardado
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error actualizando cache de promedios: {e}")
        

# ============================================
# DEBERES
# ============================================



class Deber(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('activo', 'Activo'),
        ('cerrado', 'Cerrado'),
    ]
    
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField()
    teacher = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='deberes_profesor')
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='deberes', null=True, blank=True)
    puntos_totales = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    archivo_adjunto = models.FileField(upload_to='deberes/adjuntos/', blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')

    estudiantes_especificos = models.ManyToManyField(Usuario, related_name='deberes_asignados', blank=True)
    
    class Meta:
        verbose_name_plural = "Deberes"
        ordering = ['-fecha_entrega']
    
    def __str__(self):
        return f"{self.titulo} - {self.clase.subject}"
    

    
    def entregas_completadas(self):
        return self.entregas.filter(estado__in=['entregado', 'revisado', 'tarde']).count()
    
    def porcentaje_entrega(self):
        total = self.total_estudiantes()
        if total == 0:
            return 0
        return round((self.entregas_completadas() / total) * 100, 1)
    
    def esta_vencido(self):
        return timezone.now() > self.fecha_entrega

class DeberEntrega(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('entregado', 'Entregado'),
        ('revisado', 'Revisado'),
        ('tarde', 'Entregado Tarde'),
    ]
    
    deber = models.ForeignKey(Deber, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mis_entregas') # Changed to Usuario
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    archivo_entrega = models.FileField(upload_to='deberes/entregas/', blank=True, null=True)
    comentario = models.TextField(blank=True)
    calificacion = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    retroalimentacion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    class Meta:
        verbose_name_plural = "Entregas de Deberes"
        unique_together = ['deber', 'estudiante']
        ordering = ['-fecha_entrega']
    
    def __str__(self):
        return f"{self.deber.titulo} - {self.estudiante.nombre}" # Changed to .nombre
    
    def esta_tarde(self):
        return self.fecha_entrega > self.deber.fecha_entrega
    
    def save(self, *args, **kwargs):
        if self.estado == 'entregado' and self.esta_tarde():
            self.estado = 'tarde'
        super().save(*args, **kwargs)