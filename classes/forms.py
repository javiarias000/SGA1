from django import forms
from django.contrib.auth.models import User
from .models import Activity, Attendance, Clase, GradeLevel, Enrollment, Horario, CalificacionParcial, TipoAporte
from subjects.models import Subject
from users.models import Usuario
# Student and Teacher models are now imported locally within __init__ or methods where needed to avoid circular dependencies.
from students.models import Student # Temporarily keeping for some forms before full refactor
from teachers.models import Teacher # Temporarily keeping for some forms before full refactor


class ActivityForm(forms.ModelForm):
    """Formulario para registrar clases"""
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_subject'}))
    class Meta:
        model = Activity
        fields = [
            'student', 'clase', 'subject', 'date', 'topics_worked', 'techniques',
            'pieces', 'performance', 'practice_time', 'strengths',
            'areas_to_improve', 'homework', 'observations'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control', 'id': 'id_student'}),
            'clase': forms.Select(attrs={'class': 'form-control', 'id': 'id_clase'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'topics_worked': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Ej: Escalas mayores, lectura a primera vista...'
            }),
            'techniques': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Ej: Arpegios, picado, ligados...'
            }),
            'pieces': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Estudio No. 1 de Sor, Romanza Anónima...'
            }),
            'performance': forms.Select(attrs={'class': 'form-control'}),
            'practice_time': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 15, 
                'max': 180
            }),
            'strengths': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': '¿Qué hizo bien el estudiante?'
            }),
            'areas_to_improve': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Aspectos técnicos o musicales a trabajar...'
            }),
            'homework': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Tareas específicas para practicar en casa...'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Notas adicionales del profesor...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar estudiantes/clases asignadas al docente vía inscripciones
        if self.teacher:
            teacher_usuario = getattr(self.teacher, 'usuario', None)
            if teacher_usuario:
                self.fields['student'].queryset = Student.objects.filter(
                    usuario__enrollments_as_student__docente=teacher_usuario,
                    usuario__enrollments_as_student__estado='ACTIVO',
                    active=True
                ).distinct().order_by('name')

                self.fields['clase'].queryset = Clase.objects.filter(
                    enrollments__docente=teacher_usuario,
                    enrollments__estado='ACTIVO',
                    active=True
                ).distinct().order_by('subject', 'name')
            else:
                self.fields['student'].queryset = Student.objects.none()
                self.fields['clase'].queryset = Clase.objects.none()

            self.fields['subject'].queryset = self.teacher.subjects.all()
        
        # Valores iniciales útiles
        from datetime import date as _date
        if not self.initial.get('practice_time'):
            self.fields['practice_time'].initial = 30
        if not self.initial.get('date'):
            self.fields['date'].initial = _date.today()
        
        # Ocultar el campo class_number ya que se auto-calcula
        if 'class_number' in self.fields:
            self.fields['class_number'].widget = forms.HiddenInput()


class GradeForm(forms.ModelForm): # Renamed from GradeForm if it's for CalificacionParcial
    """Formulario para registrar calificaciones parciales"""
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    tipo_aporte = forms.ModelChoiceField(queryset=TipoAporte.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    
    class Meta:
        model = CalificacionParcial # Use CalificacionParcial model
        fields = ['student', 'subject', 'parcial', 'quimestre', 'tipo_aporte', 'calificacion', 'observaciones']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'parcial': forms.Select(attrs={'class': 'form-control'}),
            'quimestre': forms.Select(attrs={'class': 'form-control'}),
            'calificacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10,
                'step': 0.1,
                'placeholder': '0.00'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Comentarios sobre la calificación...'
            }),
            # 'fecha_registro': forms.DateInput(attrs={ # Removed 'fecha_registro'
            #     'class': 'form-control',
            #     'type': 'date'
            # }),
        }
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Valores iniciales útiles
        from datetime import date as _date
        if not self.initial.get('fecha_registro'):
            self.fields['fecha_registro'].initial = _date.today()
        
        # Filtrar solo estudiantes del docente actual
        if self.teacher:
            # Assumes teacher has 'students' related_name
            self.fields['student'].queryset = Student.objects.filter(
                usuario__enrollments_as_student__docente=self.teacher.usuario,
                usuario__enrollments_as_student__estado='ACTIVO'
            ).distinct()
            self.fields['subject'].queryset = self.teacher.subjects.all()


class AttendanceForm(forms.ModelForm):
    """Formulario para registrar asistencia"""
    class Meta:
        model = Attendance
        fields = ['student', 'date', 'status', 'notes']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones sobre la asistencia...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Valores iniciales útiles
        if not self.initial.get('status'):
            self.fields['status'].initial = 'Presente'
        from datetime import date as _date
        if not self.initial.get('date'):
            self.fields['date'].initial = _date.today()
        
        # Filtrar solo estudiantes del docente actual
        if self.teacher:
            self.fields['student'].queryset = Student.objects.filter(
                teacher=self.teacher,
                active=True
            )


class ClaseForm(forms.ModelForm):
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = Clase
        fields = ['name', 'subject', 'ciclo_lectivo', 'paralelo', 'description', 'schedule', 'room', 'max_students', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'schedule': forms.TextInput(attrs={'class': 'form-control'}),
            'room': forms.TextInput(attrs={'class': 'form-control'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        if self.teacher:
            self.fields['subject'].queryset = self.teacher.subjects.all()

    def save(self, commit=True):
        obj = super().save(commit=False)
        # `Clase` ya no tiene FK directa a Teacher.
        if commit:
            obj.save()
        return obj


class TeacherProfileForm(forms.ModelForm):
    """Formulario para editar perfil del docente.

    - Datos de identidad/contacto viven en `users.Usuario`.
    - Datos propios del perfil docente viven en `teachers.Teacher`.
    """

    nombre = forms.CharField(
        label='Nombre completo',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'})
    )
    email = forms.EmailField(
        label='Email (opcional)',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    phone = forms.CharField(
        label='Teléfono (opcional)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0999999999'})
    )
    cedula = forms.CharField(
        label='Cédula (opcional)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cédula'})
    )

    class Meta:
        model = Teacher
        fields = ['specialization', 'photo'] # 'subjects' removed
        widgets = {
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Guitarra Clásica, Teoría Musical...'
            }),
            # 'subjects': forms.SelectMultiple(attrs={'class': 'form-select'}), # 'subjects' widget removed
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'usuario_id', None):
            self.fields['nombre'].initial = self.instance.usuario.nombre
            self.fields['email'].initial = self.instance.usuario.email
            self.fields['phone'].initial = self.instance.usuario.phone
            self.fields['cedula'].initial = self.instance.usuario.cedula

    def save(self, commit=True):
        teacher = super().save(commit=False)

        if teacher.usuario_id:
            usuario = teacher.usuario
            usuario.nombre = (self.cleaned_data.get('nombre') or '').strip()
            usuario.email = (self.cleaned_data.get('email') or '').strip() or None
            usuario.phone = (self.cleaned_data.get('phone') or '').strip() or None
            usuario.cedula = (self.cleaned_data.get('cedula') or '').strip() or None
            usuario.rol = Usuario.Rol.DOCENTE
            usuario.save()

        if commit:
            teacher.save()
            self.save_m2m()

        return teacher


class UnifiedEntryForm(forms.Form):
    """Formulario unificado para registrar Clase, Asistencia y Calificación en una sola vista."""
    # Comunes
    common_student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Estudiante'
    )
    common_subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Materia'
    )
    common_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Fecha'
    )

    # Clase (Activity)
    performance = forms.ChoiceField(
        choices=Activity.PERFORMANCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='Bueno',
        label='Desempeño'
    )
    practice_time = forms.IntegerField(
        min_value=15, max_value=180,
        initial=30,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Minutos de práctica'
    )
    topics_worked = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Temas trabajados'
    )
    techniques = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Técnicas'
    )
    pieces = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Repertorio'
    )
    strengths = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Fortalezas'
    )
    areas_to_improve = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Áreas a mejorar'
    )
    homework = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Tareas para casa'
    )
    observations = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Observaciones'
    )

    # Asistencia
    attendance_status = forms.ChoiceField(
        choices=Attendance.STATUS_CHOICES,
        initial='Presente',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Asistencia'
    )
    attendance_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Notas de asistencia'
    )

    # Calificación
    grade_period = forms.ChoiceField(
        choices=CalificacionParcial.PARCIAL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Parcial'
    )
    grade_score = forms.DecimalField(
        required=False,
        min_value=0, max_value=10, decimal_places=2, max_digits=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        label='Nota'
    )
    grade_comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Observaciones de Calificación'
    )

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        from datetime import date as _date
        if not self.initial.get('common_date'):
            self.fields['common_date'].initial = _date.today()
        if self.teacher:
            self.fields['common_student'].queryset = Student.objects.filter(teacher=self.teacher, active=True)
            self.fields['common_subject'].queryset = self.teacher.subjects.all()

    def clean(self):
        cleaned = super().clean()
        # Validación condicional para calificación
        score = cleaned.get('grade_score')
        parcial = cleaned.get('grade_period') # Renamed from 'period' to 'parcial' for clarity
        if score is not None and parcial in (None, ''):
            self.add_error('grade_period', 'Selecciona el período para la calificación')
        return cleaned


class QuickAttendanceForm(forms.Form):
    """Formulario rápido para marcar asistencia de múltiples estudiantes"""
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Fecha'
    )
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if self.teacher:
            students = Student.objects.filter(teacher=self.teacher, active=True)
            
            for student in students:
                self.fields[f'student_{student.id}'] = forms.ChoiceField(
                    choices=Attendance.STATUS_CHOICES,
                    widget=forms.Select(attrs={'class': 'form-control'}),
                    label=student.name,
                    initial='Presente'
                )

class RegisterForm(forms.Form):
    """Formulario de registro de docentes"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario (sin espacios)',
            'required': True
        }),
        label='Nombre de usuario'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com',
            'required': True
        }),
        label='Correo electrónico'
    )
    
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre',
            'required': True
        }),
        label='Nombre'
    )
    
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tus apellidos',
            'required': True
        }),
        label='Apellidos'
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0999999999'
        }),
        label='Teléfono (opcional)'
    )
    
    specialization = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Guitarra Clásica, Teoría Musical...'
        }),
        label='Especialización (opcional)'
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 6 caracteres',
            'required': True
        }),
        label='Contraseña'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repite tu contraseña',
            'required': True
        }),
        label='Confirmar contraseña'
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Este nombre de usuario ya está en uso')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo ya está registrado')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Las contraseñas no coinciden')
        
        if password1 and len(password1) < 6:
            raise forms.ValidationError('La contraseña debe tener al menos 6 caracteres')
        
        return cleaned_data
