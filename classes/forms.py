from django import forms
from django.contrib.auth.models import User
from .models import Teacher, Student, Activity, Grade, Attendance, Clase
from subjects.models import Subject

class StudentForm(forms.ModelForm):
    """Formulario para agregar/editar estudiantes"""
    class Meta:
        model = Student
        fields = ['name', 'grade', 'parent_name', 'parent_email', 'parent_phone', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del estudiante'
            }),
'grade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1ro Bachillerato A'
            }),
            'parent_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del padre/madre'
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0999999999'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales sobre el estudiante...'
            })
        }


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
        
        # Filtrar solo estudiantes del docente actual
        if self.teacher:
            self.fields['student'].queryset = Student.objects.filter(
                teacher=self.teacher,
                active=True
            )
            # Filtrar clases del docente
            self.fields['clase'].queryset = Clase.objects.filter(
                teacher=self.teacher,
                active=True
            ).order_by('subject', 'name')
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


class GradeForm(forms.ModelForm):
    """Formulario para registrar calificaciones"""
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = Grade
        fields = ['student', 'subject', 'period', 'score', 'comments', 'date']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'period': forms.Select(attrs={'class': 'form-control'}),
            'score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10,
                'step': 0.1,
                'placeholder': '0.00'
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Comentarios sobre la calificación...'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        # Valores iniciales útiles
        from datetime import date as _date
        if not self.initial.get('date'):
            self.fields['date'].initial = _date.today()
        
        # Filtrar solo estudiantes del docente actual
        if self.teacher:
            self.fields['student'].queryset = Student.objects.filter(
                teacher=self.teacher,
                active=True
            )
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
        fields = ['name', 'subject', 'description', 'schedule', 'room', 'max_students', 'active']
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
        if self.teacher is not None:
            obj.teacher = self.teacher
        if commit:
            obj.save()
        return obj


class TeacherProfileForm(forms.ModelForm):
    """Formulario para editar perfil del docente"""
    class Meta:
        model = Teacher
        fields = ['full_name', 'specialization', 'phone', 'photo']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Guitarra Clásica, Teoría Musical...'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0999999999'
            }),
        }


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
        choices=Grade.PERIOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Período'
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
        label='Comentarios'
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
        period = cleaned.get('grade_period')
        if score is not None and period in (None, ''):
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
