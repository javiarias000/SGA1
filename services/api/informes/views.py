import time
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from classes.models import GradeLevel, Clase
from students.models import Student
from subjects.models import Subject
from users.models import Usuario
from teachers.models import Teacher

from .models import (
    SesionClase, RecomendacionEstudiante,
    RegistroEnvioWhatsapp, SubmisionFormulario, ConfiguracionWhatsapp,
)
from .grades import get_grades
from .whatsapp import (
    create_instance, get_instance_status, send_text,
    normalize_phone, build_parent_message,
)
from .forms_submitter import submit_form, build_form_text


# ── Grados disponibles ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def grade_levels(request):
    """Lista todos los niveles/paralelos con tutor asignado."""
    levels = GradeLevel.objects.select_related('docente_tutor').order_by('level', 'section')
    data = []
    for gl in levels:
        data.append({
            'id': gl.pk,
            'nombre': str(gl),
            'level': gl.level,
            'section': gl.section,
            'ciclo': gl.ciclo,
            'docente_tutor': {
                'id': gl.docente_tutor.pk,
                'nombre': gl.docente_tutor.nombre,
                'phone': gl.docente_tutor.phone or '',
            } if gl.docente_tutor else None,
        })
    return Response({'grade_levels': data})


@api_view(['GET'])
@permission_classes([AllowAny])
def subjects_list(request):
    """Lista todas las materias."""
    qs = Subject.objects.order_by('name')
    return Response({'subjects': [{'id': s.pk, 'name': s.name, 'tipo': s.tipo_materia} for s in qs]})


# ── Calificaciones / notas ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def grades(request):
    """
    Devuelve calificaciones y datos de contacto para generar informes.

    Query params:
      grade_level_id  (int, requerido)
      subject_id      (int, requerido)
      periodo         (str, requerido): 1P/2P/3P/4P/1Q/2Q/Anual/A1/A2/A3/A4
      ciclo           (str, opcional, default '2025-2026')
    """
    grade_level_id = request.query_params.get('grade_level_id')
    subject_id = request.query_params.get('subject_id')
    periodo = request.query_params.get('periodo', '')
    ciclo = request.query_params.get('ciclo', '2025-2026')

    if not grade_level_id or not subject_id or not periodo:
        return Response({'error': 'Parámetros requeridos: grade_level_id, subject_id, periodo'}, status=400)

    try:
        students_data = get_grades(int(grade_level_id), int(subject_id), periodo, ciclo)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

    # Separar dificultades (nota < 7) — mismo criterio que informe-whatsapp
    dificultades = [s for s in students_data if s.get('estado') in ('DIFICULTAD', 'INASISTENCIAS', 'BAJO_ASISTENCIA')]

    return Response({
        'periodo': periodo,
        'ciclo': ciclo,
        'students': students_data,
        'dificultades': dificultades,
        'total': len(students_data),
    })


# ── Docentes ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def docentes(request):
    """Lista todos los docentes con teléfono y correos."""
    qs = Usuario.objects.filter(rol='DOCENTE').order_by('nombre')
    data = []
    for u in qs:
        teacher = getattr(u, 'teacher_profile', None)
        data.append({
            'id': u.pk,
            'nombre': u.nombre,
            # campos compatibles con el frontend Node.js
            'celular': u.phone or '',
            'phone': u.phone or '',
            'cargo': teacher.specialization if teacher else '',
            'correoInstitucional': u.email or '',
            'correoPersonal': '',
            'email': u.email or '',
            'specialization': teacher.specialization if teacher else '',
        })
    return Response({'docentes': data})


@api_view(['POST'])
@permission_classes([AllowAny])
def docente_upsert(request):
    """Crea o actualiza un docente (equivalente a /api/docentes/upsert)."""
    nombre = request.data.get('nombre', '').strip()
    if not nombre:
        return Response({'success': False, 'error': 'Falta nombre'}, status=400)

    phone_raw = request.data.get('celular') or request.data.get('phone', '')
    phone = normalize_phone(phone_raw) if phone_raw else None

    usuario, created = Usuario.objects.get_or_create(
        nombre__iexact=nombre,
        rol='DOCENTE',
        defaults={'nombre': nombre, 'rol': 'DOCENTE'},
    )
    if phone:
        usuario.phone = phone
    email = request.data.get('correoInstitucional') or request.data.get('email', '')
    if email:
        usuario.email = email
    usuario.save()

    return Response({
        'success': True,
        'docente': {
            'id': usuario.pk,
            'nombre': usuario.nombre,
            # campos compatibles con el frontend Node.js
            'celular': usuario.phone or '',
            'phone': usuario.phone or '',
            'correoInstitucional': usuario.email or '',
            'correoPersonal': '',
            'email': usuario.email or '',
            'cargo': '',
        },
    })


# ── Tutores-cursos ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def tutores_cursos(request):
    """Devuelve la tabla completa tutor-curso."""
    qs = GradeLevel.objects.select_related('docente_tutor').order_by('level', 'section')
    data = []
    for gl in qs:
        tutor = gl.docente_tutor
        teacher = getattr(tutor, 'teacher_profile', None) if tutor else None
        data.append({
            'curso_id': gl.pk,
            'curso': str(gl),
            'curso_key': f'{gl.level}_{gl.section}',
            'level': gl.level,
            'section': gl.section,
            # campos compatibles con frontend Node.js
            'docente_id': tutor.pk if tutor else None,
            'tutor_id': tutor.pk if tutor else None,
            'tutor': tutor.nombre if tutor else None,
            'celular': tutor.phone or '' if tutor else '',
            'tutor_phone': tutor.phone or '' if tutor else '',
            'cargo': teacher.specialization if teacher else '',
            'correo_institucional': tutor.email or '' if tutor else '',
            'correo_personal': '',
        })
    return Response({
        'tutores_cursos': data,
        'tutoresCursos': data,  # alias camelCase para el frontend
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def tutor_por_curso(request):
    """Devuelve el tutor de un curso específico por nombre."""
    nombre = request.query_params.get('curso', '')
    if not nombre:
        return Response({'tutor': None})

    # Intentar match exacto primero, luego por level+section
    gl = GradeLevel.objects.select_related('docente_tutor').filter(
        docente_tutor__isnull=False
    ).first()

    # Búsqueda más flexible: "5o A" → level=5, section=A
    import re
    match = re.search(r'(\d+)', nombre)
    sec_match = re.search(r'\b([ABC])\b', nombre.upper())
    if match and sec_match:
        level = match.group(1)
        section = sec_match.group(1)
        gl = GradeLevel.objects.filter(level=level, section=section).select_related('docente_tutor').first()

    if not gl or not gl.docente_tutor:
        return Response({'tutor': None})

    return Response({'tutor': {
        'id': gl.docente_tutor.pk,
        'nombre': gl.docente_tutor.nombre,
        'phone': gl.docente_tutor.phone or '',
        'email': gl.docente_tutor.email or '',
    }})


# ── WhatsApp ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def wa_instance(request):
    """Crea o reconecta instancia WhatsApp y devuelve QR."""
    instance_name = request.data.get('instanceName', '').strip()
    if not instance_name:
        return Response({'success': False, 'error': 'Falta instanceName'}, status=400)

    result = create_instance(instance_name)

    if result.get('success'):
        ConfiguracionWhatsapp.objects.update_or_create(
            nombre_instancia=instance_name,
            defaults={'activa': False},
        )

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def wa_status(request, instance_name):
    """Estado de conexión de la instancia WhatsApp."""
    result = get_instance_status(instance_name)
    if result.get('state') == 'open':
        ConfiguracionWhatsapp.objects.filter(
            nombre_instancia=instance_name
        ).update(activa=True)
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def wa_send(request):
    """Envía un mensaje de texto WhatsApp."""
    instance = request.data.get('instanceName', '').strip()
    phone = request.data.get('phone', '').strip()
    message = request.data.get('message', '').strip()

    if not instance or not phone or not message:
        return Response({'success': False, 'error': 'Faltan parámetros: instanceName, phone, message'}, status=400)

    result = send_text(instance, phone, message)
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def wa_send_grades(request):
    """
    Envío masivo de informes WhatsApp para un nivel/materia/período.
    Body:
      grade_level_id, subject_id, periodo, ciclo,
      instance_name, docente_nombre
    """
    grade_level_id = request.data.get('grade_level_id')
    subject_id = request.data.get('subject_id')
    periodo = request.data.get('periodo', '')
    ciclo = request.data.get('ciclo', '2025-2026')
    instance_name = request.data.get('instance_name', '').strip()
    docente_nombre = request.data.get('docente_nombre', '').strip()

    if not all([grade_level_id, subject_id, periodo, instance_name]):
        return Response({'error': 'Faltan parámetros'}, status=400)

    try:
        subject = Subject.objects.get(pk=subject_id)
        materia_nombre = subject.name
    except Subject.DoesNotExist:
        return Response({'error': 'Materia no encontrada'}, status=404)

    try:
        students_data = get_grades(int(grade_level_id), int(subject_id), periodo, ciclo)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

    results = []
    for st_data in students_data:
        phone_raw = st_data.get('telefono_representante', '')
        phone = normalize_phone(phone_raw) if phone_raw else None

        if not phone:
            results.append({
                'nombre': st_data['nombre'],
                'success': False,
                'error': 'Sin teléfono de representante',
            })
            continue

        mensaje = build_parent_message(st_data, materia_nombre, periodo, docente_nombre)
        wa_result = send_text(instance_name, phone, mensaje)

        # Guardar registro
        try:
            student_obj = Student.objects.get(pk=st_data['student_id'])
            RegistroEnvioWhatsapp.objects.create(
                estudiante=student_obj,
                materia=subject,
                periodo=periodo,
                ciclo_lectivo=ciclo,
                mensaje=mensaje,
                telefono_usado=phone,
                estado_wa='enviado' if wa_result.get('success') else 'fallido',
                error_wa=wa_result.get('error', ''),
            )
        except Exception:
            pass

        results.append({
            'nombre': st_data['nombre'],
            'phone': phone,
            'success': wa_result.get('success', False),
            'error': wa_result.get('error', ''),
        })

        time.sleep(0.5)  # Evitar rate limiting

    return Response({
        'total': len(results),
        'enviados': sum(1 for r in results if r['success']),
        'fallidos': sum(1 for r in results if not r['success']),
        'results': results,
    })


# ── Formularios Google ────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_forms(request):
    """
    Envía informes docentes al Google Form.
    Body:
      submissions: [{ grade_level_id, subject_id, docente_id, contenidos, acciones,
                      dropdown_option, periodo, ciclo }]
      form_url: str
      form_fields: [{ entryId, mapping }]
    """
    submissions = request.data.get('submissions', [])
    form_url = request.data.get('form_url', '').strip()
    form_fields = request.data.get('form_fields', [])

    if not form_url:
        # el frontend envía formUrl (camelCase), también aceptar esa forma
        form_url = request.data.get('formUrl', '').strip()
    if not form_url:
        return Response({'error': 'Falta form_url / formUrl'}, status=400)

    results = []
    for sub in submissions:
        # Calcular dificultades desde la BD si no se proveen
        dificultades = sub.get('dificultades')
        if dificultades is None and sub.get('grade_level_id') and sub.get('subject_id'):
            students_data = get_grades(
                int(sub['grade_level_id']), int(sub['subject_id']),
                sub.get('periodo', '2Q'), sub.get('ciclo', '2025-2026'),
            )
            dificultades = [
                {'nombre': s['nombre'], 'nota': s['nota']}
                for s in students_data
                if s.get('estado') == 'DIFICULTAD'
            ]

        contenidos = sub.get('contenidos', '')
        acciones = sub.get('acciones', '')
        form_text = build_form_text(contenidos, dificultades or [], acciones)

        submission_data = {
            'dropdown_option': sub.get('dropdown_option', ''),
            'docente': sub.get('docente', ''),
            'materia': sub.get('materia', ''),
            'contenidos': contenidos,
            'acciones': acciones,
            'dificultades': dificultades or [],
            'form_text': form_text,
        }

        result = submit_form(submission_data, form_url, form_fields)

        # Guardar historial
        try:
            docente_usuario = (
                Usuario.objects.get(pk=sub['docente_id'])
                if sub.get('docente_id') else None
            )
            subject_obj = (
                Subject.objects.get(pk=sub['subject_id'])
                if sub.get('subject_id') else None
            )
            SubmisionFormulario.objects.create(
                docente=docente_usuario,
                materia=subject_obj,
                curso_nombre=sub.get('dropdown_option', ''),
                contenidos=contenidos,
                acciones=acciones,
                dificultades_json=dificultades or [],
                form_url=form_url,
                form_fields_json=form_fields,
                exito=result.get('success', False),
                error=result.get('error', ''),
            )
        except Exception:
            pass

        label = f"{sub.get('materia', '')} — {sub.get('dropdown_option', '')}"
        results.append({
            'label': label,
            'success': result.get('success', False),
            'error': result.get('error', ''),
        })

        time.sleep(0.8)

    return Response({'results': results})


@api_view(['GET'])
@permission_classes([AllowAny])
def submissions_list(request):
    """Historial de envíos a formularios."""
    qs = SubmisionFormulario.objects.select_related('docente', 'materia').order_by('-enviado_en')[:200]
    data = []
    for s in qs:
        tutor = s.docente
        data.append({
            'id': s.pk,
            # campos compatibles con el frontend Node.js
            'tabName': '',
            'curso': s.curso_nombre,
            'materia': s.materia.name if s.materia else '',
            'docenteNombre': tutor.nombre if tutor else '',
            'docente': tutor.nombre if tutor else '',
            'docentePhone': normalize_phone(tutor.phone) if tutor and tutor.phone else '',
            'contenidos': s.contenidos,
            'acciones': s.acciones,
            'dificultades': s.dificultades_json or [],
            'students': [],
            'sentAt': s.enviado_en.isoformat(),
            'waSentAt': None,
            'formUrl': s.form_url,
            'formSentCount': s.veces_enviado,
            'lastFormSentAt': None,
            'exito': s.exito,
            'error': s.error,
        })
    return Response({'submissions': data})


@api_view(['POST'])
@permission_classes([AllowAny])
def submission_resend(request, pk):
    """Reenvía una submisión guardada al formulario."""
    try:
        sub = SubmisionFormulario.objects.get(pk=pk)
    except SubmisionFormulario.DoesNotExist:
        return Response({'success': False, 'error': 'No encontrado'}, status=404)

    if not sub.form_url:
        return Response({'success': False, 'error': 'Sin URL de formulario guardada'}, status=400)

    submission_data = {
        'dropdown_option': sub.curso_nombre,
        'docente': sub.docente.nombre if sub.docente else '',
        'materia': sub.materia.name if sub.materia else '',
        'contenidos': sub.contenidos,
        'acciones': sub.acciones,
        'dificultades': sub.dificultades_json,
        'form_text': build_form_text(sub.contenidos, sub.dificultades_json, sub.acciones),
    }

    result = submit_form(submission_data, sub.form_url, sub.form_fields_json)
    if result.get('success'):
        sub.veces_enviado += 1
        sub.exito = True
        sub.save(update_fields=['veces_enviado', 'exito'])

    return Response(result)


# ── Historial WhatsApp ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def wa_historial(request):
    """Historial de mensajes WhatsApp enviados."""
    qs = RegistroEnvioWhatsapp.objects.select_related(
        'estudiante__usuario', 'materia'
    ).order_by('-enviado_en')[:200]

    data = [{
        'id': r.pk,
        'estudiante': r.estudiante.usuario.nombre if r.estudiante.usuario else '',
        'materia': r.materia.name if r.materia else '',
        'periodo': r.periodo,
        'ciclo': r.ciclo_lectivo,
        'telefono': r.telefono_usado,
        'estado_wa': r.estado_wa,
        'estado_form': r.estado_form,
        'enviado_en': r.enviado_en.isoformat(),
    } for r in qs]
    return Response({'historial': data})


# ── Sesiones de clase ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def sesiones_clase(request, clase_id):
    """Lista sesiones de clase con recomendaciones."""
    sesiones = SesionClase.objects.filter(clase_id=clase_id).prefetch_related(
        'recomendaciones__estudiante'
    ).order_by('fecha', 'col_index')

    data = []
    for s in sesiones:
        data.append({
            'id': s.pk,
            'fecha': s.fecha.isoformat() if s.fecha else None,
            'tema': s.tema,
            'descripcion': s.descripcion,
            'col_index': s.col_index,
            'recomendaciones': [{
                'estudiante_id': r.estudiante.pk,
                'estudiante': r.estudiante.nombre,
                'recomendacion': r.recomendacion,
            } for r in s.recomendaciones.all()],
        })
    return Response({'sesiones': data})


@api_view(['POST'])
@permission_classes([AllowAny])
def sesion_upsert(request):
    """Crea o actualiza una sesión de clase."""
    clase_id = request.data.get('clase_id')
    sheet_id = request.data.get('sheet_id', '')
    tab = request.data.get('tab', '')
    col_index = request.data.get('col_index')
    tema = request.data.get('tema', '')
    descripcion = request.data.get('descripcion', '')
    fecha = request.data.get('fecha')

    if not clase_id:
        return Response({'success': False, 'error': 'Falta clase_id'}, status=400)

    defaults = {'tema': tema, 'descripcion': descripcion, 'clase_id': clase_id}
    if fecha:
        defaults['fecha'] = fecha

    if sheet_id and tab and col_index is not None:
        sesion, _ = SesionClase.objects.update_or_create(
            sheet_id=sheet_id, tab=tab, col_index=col_index,
            defaults=defaults,
        )
    else:
        sesion = SesionClase.objects.create(**defaults)

    return Response({'success': True, 'id': sesion.pk})


@api_view(['POST'])
@permission_classes([AllowAny])
def recomendacion_upsert(request):
    """Crea o actualiza una recomendación para un estudiante en una sesión."""
    sesion_id = request.data.get('sesion_id')
    estudiante_id = request.data.get('estudiante_id')
    recomendacion = request.data.get('recomendacion', '')

    if not sesion_id or not estudiante_id:
        return Response({'success': False, 'error': 'Faltan sesion_id o estudiante_id'}, status=400)

    try:
        sesion = SesionClase.objects.get(pk=sesion_id)
        estudiante = Usuario.objects.get(pk=estudiante_id)
    except (SesionClase.DoesNotExist, Usuario.DoesNotExist) as e:
        return Response({'success': False, 'error': str(e)}, status=404)

    rec, _ = RecomendacionEstudiante.objects.update_or_create(
        sesion=sesion,
        estudiante=estudiante,
        defaults={'recomendacion': recomendacion},
    )
    return Response({'success': True, 'id': rec.pk})


@api_view(['POST'])
@permission_classes([AllowAny])
def submission_mark_wa_sent(request, pk):
    """Marca una submisión como enviada por WhatsApp."""
    try:
        sub = SubmisionFormulario.objects.get(pk=pk)
    except SubmisionFormulario.DoesNotExist:
        return Response({'success': False, 'error': 'No encontrado'}, status=404)

    sub.exito = True
    sub.save(update_fields=['exito'])
    return Response({'success': True})
