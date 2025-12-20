from django import forms
from django.contrib import admin
# from django.contrib.admin.widgets import AutocompleteSelectMultiple, AutocompleteSelect
from classes.models import Clase, Enrollment
from users.models import Usuario

class EnrollStudentForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE),
        label="Estudiante",
        widget=forms.Select(attrs={'data-placeholder': 'Seleccione un estudiante...'}),
        required=True
    )
    
    classes = forms.ModelMultipleChoiceField(
        queryset=Clase.objects.all(),
        label="Clases a Matricular",
        widget=forms.SelectMultiple(attrs={'data-placeholder': 'Seleccione una o varias clases...'}),
        required=True
    )

    # You might want to add academic cycle, or other enrollment specific details here.
    # For simplicity, we'll rely on the default values of Enrollment for now.

    # You might want to add academic cycle, or other enrollment specific details here.
    # For simplicity, we'll rely on the default values of Enrollment for now.