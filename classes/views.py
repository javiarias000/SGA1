import json

from django.contrib import messages, admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from classes.forms import EnrollStudentForm
from classes.models import Clase, Enrollment, GradeLevel
from users.models import Usuario

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


# ──────────────────────────────────────────────
# TABLERO DE PLANIFICACIÓN (drag & drop)
# ──────────────────────────────────────────────

@staff_member_required
def planificacion_view(request):
    """Vista visual para asignar docentes a materias por nivel/paralelo."""
    ciclo_lectivo = request.GET.get('ciclo', '2025-2026')

    niveles = GradeLevel.objects.prefetch_related(
        'malla_curricular__subject',
        'clases__subject',
        'clases__docente_base',
    ).order_by('level', 'section')

    docentes = Usuario.objects.filter(rol='DOCENTE').order_by('nombre')

    # Armar estructura: nivel → lista de tarjetas materia
    tablero = []
    for nivel in niveles:
        materias_en_malla = nivel.malla_curricular.select_related('subject').order_by('orden', 'subject__name')
        tarjetas = []
        for entrada in materias_en_malla:
            subject = entrada.subject
            # Buscar clase existente para este nivel+materia+ciclo
            clase = nivel.clases.filter(subject=subject, ciclo_lectivo=ciclo_lectivo).first()
            tarjetas.append({
                'subject_id': subject.id,
                'subject_name': subject.name,
                'tipo': subject.tipo_materia,
                'obligatoria': entrada.obligatoria,
                'clase_id': clase.id if clase else None,
                'docente_id': clase.docente_base_id if clase and clase.docente_base_id else None,
                'docente_nombre': clase.docente_base.nombre if clase and clase.docente_base else None,
                'num_estudiantes': clase.get_enrolled_count() if clase else 0,
            })
        tablero.append({
            'nivel': nivel,
            'tarjetas': tarjetas,
        })

    context = {
        'title': 'Planificación de Cursos',
        'tablero': tablero,
        'docentes': docentes,
        'ciclo_lectivo': ciclo_lectivo,
        'has_permission': True,
    }
    return render(request, 'admin/planificacion.html', context)


@staff_member_required
@require_POST
def api_asignar_docente(request):
    """AJAX: asigna o quita un docente de una materia en un nivel/ciclo."""
    try:
        data = json.loads(request.body)
        nivel_id = int(data['nivel_id'])
        subject_id = int(data['subject_id'])
        docente_id = data.get('docente_id')  # None = quitar docente
        ciclo_lectivo = data.get('ciclo', '2025-2026')
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    try:
        nivel = GradeLevel.objects.get(pk=nivel_id)
    except GradeLevel.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Nivel no encontrado'}, status=404)

    docente = None
    if docente_id:
        try:
            docente = Usuario.objects.get(pk=docente_id, rol='DOCENTE')
        except Usuario.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Docente no encontrado'}, status=404)

    with transaction.atomic():
        from subjects.models import Subject
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Materia no encontrada'}, status=404)

        clase, _ = Clase.objects.get_or_create(
            grade_level=nivel,
            subject=subject,
            ciclo_lectivo=ciclo_lectivo,
            defaults={
                'name': f"{subject.name} — {nivel.nombre_completo}",
                'paralelo': nivel.section,
            },
        )
        clase.docente_base = docente
        clase.save(update_fields=['docente_base'])

        # Propagar a inscripciones activas que no tengan docente propio
        Enrollment.objects.filter(
            clase=clase,
            estado='ACTIVO',
            docente__isnull=True,
        ).update(docente=docente)

    return JsonResponse({
        'ok': True,
        'clase_id': clase.id,
        'docente_nombre': docente.nombre if docente else None,
    })