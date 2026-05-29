from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.db.models import Q

import json
from .models import SolicitudMatricula, DocumentoMatricula
from .forms import DatosPersonalesForm, DocumentosForm, SecretariaRevisionForm
from .malla_curricular import get_materias_para_anio, INSTRUMENTOS


def _malla_json():
    """Dict {año: [materias]} serializado para JS."""
    return json.dumps({i: get_materias_para_anio(i) for i in range(1, 12)})


# ─── HELPERS ────────────────────────────────────────────────────────────────

def _ciclo_actual():
    today = date.today()
    return f"{today.year}-{today.year + 1}"


def _guardar_documento(solicitud, archivo, tipo):
    doc = DocumentoMatricula(
        solicitud=solicitud,
        tipo=tipo,
        nombre_original=archivo.name,
        archivo=archivo,
    )
    doc.save()
    return doc


# ─── VISTA PÚBLICA: NUEVA INSCRIPCIÓN ───────────────────────────────────────

class NuevaMatriculaView(View):
    """
    Formulario público en dos pasos para aspirantes nuevos.
    Paso 1 (GET/POST): datos personales → guardados en session.
    Paso 2 (GET/POST): subida de documentos → crea SolicitudMatricula.
    """

    def get(self, request):
        paso = request.session.get('matricula_paso', 1)
        if paso == 2 and 'matricula_datos' in request.session:
            form = DocumentosForm()
            return render(request, 'matriculas/nueva_paso2.html', {
                'form': form,
                'datos': request.session['matricula_datos'],
            })
        form = DatosPersonalesForm()
        return render(request, 'matriculas/nueva_paso1.html', {
            'form': form,
            'instrumentos': INSTRUMENTOS,
            'malla_json': _malla_json(),
        })

    def post(self, request):
        paso = request.session.get('matricula_paso', 1)

        if paso == 1 or 'siguiente' in request.POST:
            form = DatosPersonalesForm(request.POST)
            if form.is_valid():
                request.session['matricula_datos'] = form.cleaned_data
                request.session['matricula_datos']['fecha_nacimiento'] = str(form.cleaned_data['fecha_nacimiento'])
                request.session['matricula_paso'] = 2
                return redirect('matriculas:nueva')
            return render(request, 'matriculas/nueva_paso1.html', {
                'form': form,
                'instrumentos': INSTRUMENTOS,
                'malla_json': _malla_json(),
            })

        if paso == 2:
            if 'volver' in request.POST:
                request.session['matricula_paso'] = 1
                datos = request.session.get('matricula_datos', {})
                form = DatosPersonalesForm(initial=datos)
                return render(request, 'matriculas/nueva_paso1.html', {
                    'form': form,
                    'instrumentos': INSTRUMENTOS,
                    'malla_json': _malla_json(),
                })

            form = DocumentosForm(request.POST, request.FILES)
            if form.is_valid():
                datos = request.session.get('matricula_datos', {})
                anio = int(datos.get('anio_solicitado', 1))

                solicitud = SolicitudMatricula.objects.create(
                    tipo=SolicitudMatricula.TipoSolicitud.NUEVA,
                    nombre_completo=datos['nombre_completo'],
                    cedula=datos['cedula'],
                    fecha_nacimiento=datos['fecha_nacimiento'],
                    nombre_representante=datos.get('nombre_representante', ''),
                    email_representante=datos['email_representante'],
                    phone_representante=datos['phone_representante'],
                    direccion=datos.get('direccion', ''),
                    ciudad=datos.get('ciudad', ''),
                    anio_solicitado=anio,
                    instrumento_elegido=datos.get('instrumento_elegido', ''),
                    ciclo_lectivo=datos.get('ciclo_lectivo', _ciclo_actual()),
                )

                _guardar_documento(solicitud, request.FILES['cedula_doc'], DocumentoMatricula.TipoDocumento.CEDULA)
                _guardar_documento(solicitud, request.FILES['cert_educacion_doc'], DocumentoMatricula.TipoDocumento.CERT_EDUCACION)
                if request.FILES.get('cert_conservatorio_doc'):
                    _guardar_documento(solicitud, request.FILES['cert_conservatorio_doc'], DocumentoMatricula.TipoDocumento.CERT_CONSERVATORIO)
                _guardar_documento(solicitud, request.FILES['foto_carnet_doc'], DocumentoMatricula.TipoDocumento.FOTO_CARNET)

                # Lanzar tarea IA asíncrona
                try:
                    from .tasks import analizar_documentos_solicitud
                    analizar_documentos_solicitud.delay(solicitud.pk)
                except Exception:
                    pass

                # Limpiar session
                request.session.pop('matricula_datos', None)
                request.session.pop('matricula_paso', None)

                return redirect('matriculas:confirmacion', codigo=solicitud.codigo_seguimiento)

            return render(request, 'matriculas/nueva_paso2.html', {
                'form': form,
                'datos': request.session.get('matricula_datos', {}),
            })

        return redirect('matriculas:nueva')


def confirmacion_view(request, codigo):
    solicitud = get_object_or_404(SolicitudMatricula, codigo_seguimiento=codigo)
    materias = get_materias_para_anio(solicitud.anio_solicitado)
    return render(request, 'matriculas/confirmacion.html', {
        'solicitud': solicitud,
        'materias': materias,
    })


def seguimiento_view(request):
    """Consulta pública del estado de solicitud por código o cédula."""
    solicitud = None
    error = None

    if request.method == 'POST':
        busqueda = request.POST.get('busqueda', '').strip()
        try:
            # intentar por UUID
            import uuid
            codigo = uuid.UUID(busqueda)
            solicitud = SolicitudMatricula.objects.filter(codigo_seguimiento=codigo).first()
        except ValueError:
            # buscar por cédula
            solicitud = SolicitudMatricula.objects.filter(cedula=busqueda).order_by('-created_at').first()

        if not solicitud:
            error = 'No se encontró ninguna solicitud con ese código o cédula.'

    return render(request, 'matriculas/seguimiento.html', {'solicitud': solicitud, 'error': error})


# ─── VISTA ESTUDIANTE AUTENTICADO: RENOVACIÓN ───────────────────────────────

@login_required
def renovacion_view(request):
    usuario = request.user
    ciclo = _ciclo_actual()

    # Verificar si ya tiene solicitud este ciclo
    solicitud_existente = SolicitudMatricula.objects.filter(
        usuario=usuario, ciclo_lectivo=ciclo
    ).order_by('-created_at').first()

    if solicitud_existente and solicitud_existente.estado not in [
        SolicitudMatricula.Estado.RECHAZADA
    ]:
        return render(request, 'matriculas/renovacion_existente.html', {
            'solicitud': solicitud_existente,
            'materias': get_materias_para_anio(solicitud_existente.anio_solicitado),
        })

    # Detectar año automáticamente desde historial
    from classes.models import Enrollment
    ultimo_anio = 1
    try:
        ultima_matricula = SolicitudMatricula.objects.filter(
            usuario=usuario, estado=SolicitudMatricula.Estado.APROBADA
        ).order_by('-created_at').first()
        if ultima_matricula:
            ultimo_anio = min(ultima_matricula.anio_solicitado + 1, 11)
    except Exception:
        pass

    if request.method == 'POST':
        form = DocumentosForm(request.POST, request.FILES)
        if form.is_valid():
            # Obtener datos del perfil del usuario
            try:
                nombre = usuario.usuario_profile.nombre
                cedula = usuario.usuario_profile.cedula or ''
            except Exception:
                nombre = usuario.get_full_name() or usuario.username
                cedula = ''

            solicitud = SolicitudMatricula.objects.create(
                tipo=SolicitudMatricula.TipoSolicitud.RENOVACION,
                usuario=usuario,
                nombre_completo=nombre,
                cedula=cedula,
                fecha_nacimiento=date(2000, 1, 1),  # placeholder, se actualiza del perfil
                email_representante=usuario.email or '',
                phone_representante='',
                anio_solicitado=ultimo_anio,
                ciclo_lectivo=ciclo,
            )

            _guardar_documento(solicitud, request.FILES['cedula_doc'], DocumentoMatricula.TipoDocumento.CEDULA)
            _guardar_documento(solicitud, request.FILES['cert_educacion_doc'], DocumentoMatricula.TipoDocumento.CERT_EDUCACION)
            if request.FILES.get('cert_conservatorio_doc'):
                _guardar_documento(solicitud, request.FILES['cert_conservatorio_doc'], DocumentoMatricula.TipoDocumento.CERT_CONSERVATORIO)
            _guardar_documento(solicitud, request.FILES['foto_carnet_doc'], DocumentoMatricula.TipoDocumento.FOTO_CARNET)

            try:
                from .tasks import analizar_documentos_solicitud
                analizar_documentos_solicitud.delay(solicitud.pk)
            except Exception:
                pass

            messages.success(request, f'Tu solicitud de renovación fue enviada exitosamente. Código: {solicitud.codigo_seguimiento}')
            return redirect('matriculas:confirmacion', codigo=solicitud.codigo_seguimiento)
    else:
        form = DocumentosForm()

    materias_proximas = get_materias_para_anio(ultimo_anio)
    return render(request, 'matriculas/renovacion.html', {
        'form': form,
        'anio_siguiente': ultimo_anio,
        'materias': materias_proximas,
        'ciclo': ciclo,
    })


# ─── VISTA SECRETARÍA ───────────────────────────────────────────────────────

@login_required
def secretaria_lista_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('users:dashboard')

    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    solicitudes = SolicitudMatricula.objects.select_related('usuario').prefetch_related('documentos').all()

    if estado_filtro:
        solicitudes = solicitudes.filter(estado=estado_filtro)
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(nombre_completo__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )

    # Contadores para el panel
    stats = {
        'total': SolicitudMatricula.objects.count(),
        'pendientes': SolicitudMatricula.objects.filter(estado='PENDIENTE').count(),
        'novedades': SolicitudMatricula.objects.filter(estado='NOVEDAD').count(),
        'en_revision': SolicitudMatricula.objects.filter(estado='EN_REVISION').count(),
        'aprobadas': SolicitudMatricula.objects.filter(estado='APROBADA').count(),
    }

    return render(request, 'matriculas/secretaria/lista.html', {
        'solicitudes': solicitudes,
        'stats': stats,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'estados': SolicitudMatricula.Estado.choices,
    })


@login_required
def secretaria_detalle_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('users:dashboard')

    solicitud = get_object_or_404(SolicitudMatricula, pk=pk)
    documentos = solicitud.documentos.all()
    materias = get_materias_para_anio(solicitud.anio_solicitado)

    if request.method == 'POST':
        form = SecretariaRevisionForm(request.POST, instance=solicitud)
        if form.is_valid():
            sol = form.save(commit=False)
            sol.secretaria = request.user
            sol.save()

            # Si se aprueba, crear matrículas en el sistema
            if sol.estado == SolicitudMatricula.Estado.APROBADA:
                _crear_matricula_academica(sol)
                messages.success(request, f'Solicitud aprobada. Se crearon las matrículas para {sol.anio_solicitado}° año.')
            else:
                messages.success(request, 'Estado actualizado correctamente.')
            return redirect('matriculas:secretaria_lista')
    else:
        form = SecretariaRevisionForm(instance=solicitud)

    return render(request, 'matriculas/secretaria/detalle.html', {
        'solicitud': solicitud,
        'documentos': documentos,
        'materias': materias,
        'form': form,
    })


@login_required
def secretaria_relanzar_ia_view(request, pk):
    """Re-lanza el análisis IA para una solicitud."""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    solicitud = get_object_or_404(SolicitudMatricula, pk=pk)
    try:
        from .tasks import analizar_documentos_solicitud
        analizar_documentos_solicitud.delay(solicitud.pk)
        return JsonResponse({'ok': True, 'mensaje': 'Análisis IA relanzado.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─── HELPER: crear matrículas académicas al aprobar ─────────────────────────

def _crear_matricula_academica(solicitud: SolicitudMatricula):
    """
    Al aprobar una solicitud, crea/vincula la matrícula en el sistema académico
    usando los modelos existentes (Enrollment, Clase, Subject).
    """
    from subjects.models import Subject
    from classes.models import Clase, Enrollment
    from users.models import Usuario

    materias = get_materias_para_anio(solicitud.anio_solicitado)

    # Intentar encontrar el Usuario asociado
    usuario_obj = None
    if solicitud.usuario:
        try:
            usuario_obj = solicitud.usuario.usuario_profile
        except Exception:
            pass

    if not usuario_obj:
        return  # Para nuevos sin cuenta, no se puede aún sin crear la cuenta

    for materia_data in materias:
        nombre_materia = materia_data['nombre']
        tipo = materia_data['tipo']

        # Buscar o crear la asignatura
        subject, _ = Subject.objects.get_or_create(
            name=nombre_materia,
            defaults={'tipo_materia': tipo, 'description': ''},
        )

        # Buscar clase del ciclo lectivo
        clase = Clase.objects.filter(
            subject=subject,
            ciclo_lectivo=solicitud.ciclo_lectivo,
            active=True,
        ).first()

        if clase:
            Enrollment.objects.get_or_create(
                estudiante=usuario_obj,
                clase=clase,
                defaults={'estado': 'ACTIVO'},
            )
