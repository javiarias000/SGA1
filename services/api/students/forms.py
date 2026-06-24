from django import forms

from classes.models import GradeLevel
from users.models import Usuario

from .models import Student


class StudentForm(forms.ModelForm):
    """Formulario para agregar/editar estudiantes.

    Student ya no tiene el campo `name`; el nombre vive en `users.Usuario`.
    """

    nombre = forms.CharField(
        label='Nombre completo',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo del estudiante'})
    )
    email = forms.EmailField(
        label='Email (opcional)',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    cedula = forms.CharField(
        label='Cédula (opcional)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cédula'})
    )

    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(),
        label="Grado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Student
        fields = ['grade_level', 'parent_name', 'parent_email', 'parent_phone', 'notes', 'active']
        widgets = {
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
            }),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'usuario_id', None):
            self.fields['nombre'].initial = self.instance.usuario.nombre
            self.fields['email'].initial = self.instance.usuario.email
            self.fields['cedula'].initial = self.instance.usuario.cedula

    def save(self, commit=True):
        student = super().save(commit=False)

        nombre = (self.cleaned_data.get('nombre') or '').strip()
        email = (self.cleaned_data.get('email') or '').strip() or None
        cedula = (self.cleaned_data.get('cedula') or '').strip() or None

        usuario = student.usuario
        if usuario is None:
            lookup = {}
            if cedula:
                lookup['cedula'] = cedula
            elif email:
                lookup['email'] = email

            if lookup:
                usuario, _created = Usuario.objects.get_or_create(
                    **lookup,
                    defaults={
                        'nombre': nombre,
                        'email': email,
                        'cedula': cedula,
                        'rol': Usuario.Rol.ESTUDIANTE,
                    }
                )
            else:
                usuario = Usuario.objects.create(
                    nombre=nombre,
                    email=email,
                    cedula=cedula,
                    rol=Usuario.Rol.ESTUDIANTE,
                )
        else:
            usuario.nombre = nombre
            usuario.email = email
            usuario.cedula = cedula
            usuario.rol = Usuario.Rol.ESTUDIANTE
            usuario.save()

        student.usuario = usuario

        if commit:
            student.save()
            self.save_m2m()

        return student
