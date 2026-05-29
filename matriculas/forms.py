from django import forms
from .models import SolicitudMatricula, DocumentoMatricula
from .malla_curricular import INSTRUMENTOS
from datetime import date


INSTRUMENTO_CHOICES = [('', '— Selecciona un instrumento —')] + [(i, i) for i in INSTRUMENTOS]

ANIO_CHOICES = [(i, f'{i}° Año (edad mínima {6 + i} años)') for i in range(1, 12)]


class DatosPersonalesForm(forms.Form):
    nombre_completo = forms.CharField(
        max_length=150,
        label='Nombre completo del estudiante',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Juan Carlos Pérez López'}),
    )
    cedula = forms.CharField(
        max_length=20,
        label='Número de cédula / documento de identidad',
        widget=forms.TextInput(attrs={'placeholder': '1234567890'}),
    )
    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    nombre_representante = forms.CharField(
        max_length=150,
        label='Nombre del representante legal',
        widget=forms.TextInput(attrs={'placeholder': 'Padre, madre o tutor'}),
    )
    email_representante = forms.EmailField(
        label='Correo electrónico del representante',
        widget=forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
    )
    phone_representante = forms.CharField(
        max_length=20,
        label='Teléfono del representante',
        widget=forms.TextInput(attrs={'placeholder': '0999123456'}),
    )
    direccion = forms.CharField(
        max_length=255,
        label='Dirección de domicilio',
        widget=forms.TextInput(attrs={'placeholder': 'Calle y número, barrio'}),
        required=False,
    )
    ciudad = forms.CharField(
        max_length=80,
        label='Ciudad',
        widget=forms.TextInput(attrs={'placeholder': 'Ambato'}),
        required=False,
    )
    anio_solicitado = forms.ChoiceField(
        choices=ANIO_CHOICES,
        label='Año al que desea ingresar',
    )
    instrumento_elegido = forms.ChoiceField(
        choices=INSTRUMENTO_CHOICES,
        label='Instrumento principal (solo 1° año)',
        required=False,
        help_text='Obligatorio únicamente para estudiantes que ingresan a 1° año.',
    )
    ciclo_lectivo = forms.CharField(
        max_length=12,
        label='Ciclo lectivo',
        initial=f'{date.today().year}-{date.today().year + 1}',
        widget=forms.TextInput(attrs={'placeholder': '2025-2026'}),
    )

    def clean(self):
        cleaned = super().clean()
        anio = int(cleaned.get('anio_solicitado', 2))
        instrumento = cleaned.get('instrumento_elegido', '')
        if anio == 1 and not instrumento:
            self.add_error('instrumento_elegido', 'Debe seleccionar un instrumento para ingresar a 1° año.')
        return cleaned


class DocumentosForm(forms.Form):
    cedula_doc = forms.FileField(
        label='Copia de Cédula / Acta de Nacimiento',
        help_text='Formato: PDF, JPG o PNG. Máximo 5 MB.',
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    cert_educacion_doc = forms.FileField(
        label='Certificado de aprobación de Educación Regular',
        help_text='Certificado del año anterior en escuela/colegio. PDF, JPG o PNG.',
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    cert_conservatorio_doc = forms.FileField(
        label='Certificado del Conservatorio (año anterior)',
        help_text='Requerido para 2° año en adelante. No aplica para nuevos en 1°.',
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    foto_carnet_doc = forms.FileField(
        label='Foto carnet del estudiante',
        help_text='Foto reciente fondo blanco. JPG o PNG.',
        widget=forms.ClearableFileInput(attrs={'accept': '.jpg,.jpeg,.png'}),
    )

    def clean(self):
        cleaned = super().clean()
        max_size = 5 * 1024 * 1024  # 5 MB
        for field_name in ['cedula_doc', 'cert_educacion_doc', 'cert_conservatorio_doc', 'foto_carnet_doc']:
            f = cleaned.get(field_name)
            if f and f.size > max_size:
                self.add_error(field_name, 'El archivo supera el límite de 5 MB.')
        return cleaned


class SecretariaRevisionForm(forms.ModelForm):
    class Meta:
        model = SolicitudMatricula
        fields = ['estado', 'notas_secretaria']
        widgets = {
            'notas_secretaria': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Observaciones para el solicitante...'}),
        }
        labels = {
            'estado': 'Cambiar estado',
            'notas_secretaria': 'Notas / observaciones',
        }
