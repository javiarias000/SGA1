from django import forms
from classes.models import Deber, DeberEntrega, Clase
from django.contrib.auth.models import User

from teachers.models import Teacher 
from users.models import Usuario # Added import
# Removed: from subjects.models import Subject

class DeberForm(forms.ModelForm):
    # Removed: subject field



    estudiantes_especificos = forms.ModelMultipleChoiceField(
        queryset=Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Estudiantes Específicos (opcional)",
        help_text="Deja vacío para asignar a todos los estudiantes"
    )

    class Meta:
        model = Deber
        fields = ['titulo', 'descripcion', 'clase', 'fecha_entrega',
                  'puntos_totales', 'archivo_adjunto', 'estado', 'estudiantes_especificos']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Tarea de Matemáticas - Capítulo 5'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Instrucciones detalladas para los estudiantes...'
            }),
            'clase': forms.Select(attrs={'class': 'form-select'}),
            'fecha_entrega': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'puntos_totales': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'value': '10'
            }),
            'archivo_adjunto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip'
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

        labels = {
            'clase': 'Materia' # Reverted label to 'Materia'
        }

    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)  # recibimos la instancia de Teacher
        super().__init__(*args, **kwargs)

        if teacher:
            # Removed: subject_queryset = teacher.subjects.all()
            # Removed: print(f"DEBUG: Subjects for teacher {teacher.full_name}: {subject_queryset}")
            # Removed: self.fields['subject'].queryset = subject_queryset
            # Filtrar solo las clases del profesor
            self.fields['clase'].queryset = Clase.objects.filter(teacher=teacher)



            # Si no hay clases, agregar mensaje de ayuda
            if not self.fields['clase'].queryset.exists():
                self.fields['clase'].help_text = "Primero debes tener clases asignadas"


class DeberEntregaForm(forms.ModelForm):
    class Meta:
        model = DeberEntrega
        fields = ['archivo_entrega', 'comentario']
        widgets = {
            'archivo_entrega': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.zip,.jpg,.png,.txt'
            }),
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Comentarios adicionales sobre tu entrega (opcional)...'
            }),
        }
        labels = {
            'archivo_entrega': 'Archivo de Entrega',
            'comentario': 'Comentarios'
        }

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = DeberEntrega
        fields = ['calificacion', 'retroalimentacion']
        widgets = {
            'calificacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'placeholder': 'Calificación'
            }),
            'retroalimentacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Retroalimentación para el estudiante...'
            }),
        }
        labels = {
            'calificacion': 'Calificación',
            'retroalimentacion': 'Retroalimentación'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer el máximo de puntos basado en el deber
        if self.instance and self.instance.deber:
            max_puntos = float(self.instance.deber.puntos_totales)
            self.fields['calificacion'].widget.attrs['max'] = max_puntos
            self.fields['calificacion'].help_text = f"Máximo: {max_puntos} puntos"