from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction

from classes.forms import EnrollStudentForm
from classes.models import Enrollment, Usuario # Import Usuario here to correctly reference it

@staff_member_required
def enroll_student_view(request):
    if request.method == 'POST':
        form = EnrollStudentForm(request.POST)
        if form.is_valid():
            student_usuario = form.cleaned_data['student']
            classes_to_enroll = form.cleaned_data['classes']
            
            enrollments_created = 0
            enrollments_updated = 0
            errors = []

            with transaction.atomic():
                for clase in classes_to_enroll:
                    # Check if an enrollment already exists for this student and class
                    enrollment, created = Enrollment.objects.get_or_create(
                        estudiante=student_usuario,
                        clase=clase,
                        defaults={
                            'estado': Enrollment.Estado.ACTIVO,
                            'tipo_materia': clase.subject.tipo_materia if clase.subject else 'TEORICA', # Default type from class's subject
                        }
                    )
                    if created:
                        enrollments_created += 1
                    elif enrollment.estado != Enrollment.Estado.ACTIVO:
                        enrollment.estado = Enrollment.Estado.ACTIVO
                        enrollment.save(update_fields=['estado'])
                        enrollments_updated += 1
                    else:
                        errors.append(f"El estudiante {student_usuario.nombre} ya está matriculado en la clase {clase.name}.")

            if enrollments_created > 0:
                messages.success(request, f"{enrollments_created} nueva(s) matrícula(s) creada(s) exitosamente.")
            if enrollments_updated > 0:
                messages.info(request, f"{enrollments_updated} matrícula(s) existente(s) actualizada(s) a estado 'ACTIVO'.")
            for error_msg in errors:
                messages.warning(request, error_msg)

            return redirect('admin:classes_enrollment_changelist') # Redirect to enrollment list

    else:
        form = EnrollStudentForm()
    
    context = {
        'form': form,
        'title': 'Matricular Estudiante en Múltiples Clases',
        'has_permission': True, # Staff member required decorator handles this
        'site_header': admin.site.site_header,
        'site_title': admin.site.site_title,
        'index_title': admin.site.index_title,
    }
    return render(request, 'admin/enroll_student_form.html', context)