import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import ConfiguracionInstitucion
from subjects.models import Subject
from classes.models import GradeLevel, Clase, Enrollment, TipoAporte
from users.models import Usuario
from teachers.models import Teacher
from students.models import Student
from informes.models import ConfiguracionWhatsapp

is_staff = lambda u: u.is_staff or u.is_superuser


STEPS = [
    {'id': 'institucion',   'titulo': 'Institución',       'url': 'setup:institucion',   'desc': 'Nombre, ciudad y año lectivo'},
    {'id': 'materias',      'titulo': 'Materias',          'url': 'setup:materias',      'desc': 'Asignaturas: instrumento, teoría, agrupación'},
    {'id': 'tipos_aporte',  'titulo': 'Tipos de Aporte',   'url': 'setup:tipos_aporte',  'desc': 'Trabajos, exposiciones, transcripciones…'},
    {'id': 'niveles',       'titulo': 'Niveles / Cursos',  'url': 'setup:niveles',       'desc': 'Años y paralelos del conservatorio'},
    {'id': 'docentes',      'titulo': 'Docentes',          'url': 'setup:docentes',      'desc': 'Registro de profesores'},
    {'id': 'clases',        'titulo': 'Clases',            'url': 'setup:clases',        'desc': 'Materia + docente + nivel'},
    {'id': 'estudiantes',   'titulo': 'Estudiantes',       'url': 'setup:estudiantes',   'desc': 'Registro de alumnos y representantes'},
    {'id': 'matriculas',    'titulo': 'Matrículas',        'url': 'setup:matriculas',    'desc': 'Inscripción de estudiantes en clases'},
    {'id': 'whatsapp',      'titulo': 'WhatsApp',          'url': 'setup:whatsapp',      'desc': 'Notificaciones automáticas a representantes'},
]


def _completion():
    cfg = ConfiguracionInstitucion.get()
    return {
        'institucion':  bool(cfg.nombre),
        'materias':     Subject.objects.exists(),
        'tipos_aporte': TipoAporte.objects.filter(activo=True).exists(),
        'niveles':      GradeLevel.objects.exists(),
        'docentes':     Usuario.objects.filter(rol='DOCENTE').exists(),
        'clases':       Clase.objects.exists(),
        'estudiantes':  Student.objects.exists(),
        'matriculas':   Enrollment.objects.exists(),
        'whatsapp':     ConfiguracionWhatsapp.objects.exists(),
    }


def _ctx(current_id):
    done = _completion()
    steps = []
    for i, s in enumerate(STEPS):
        steps.append({**s, 'numero': i + 1, 'done': done.get(s['id'], False), 'active': s['id'] == current_id})
    total = len(STEPS)
    completed = sum(1 for s in steps if s['done'])
    return {
        'steps': steps,
        'current_step_id': current_id,
        'total_steps': total,
        'completed_steps': completed,
        'progress_pct': int(completed / total * 100),
    }


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def wizard_home(request):
    done = _completion()
    for step in STEPS:
        if not done.get(step['id']):
            return redirect(f"setup:{step['id']}")
    return redirect('setup:whatsapp')


# ─── PASO 1: Institución ──────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_institucion(request):
    cfg = ConfiguracionInstitucion.get()
    if request.method == 'POST':
        cfg.nombre = request.POST.get('nombre', '').strip()
        cfg.siglas = request.POST.get('siglas', '').strip()
        cfg.ciudad = request.POST.get('ciudad', '').strip()
        cfg.direccion = request.POST.get('direccion', '').strip()
        cfg.telefono = request.POST.get('telefono', '').strip()
        cfg.email = request.POST.get('email', '').strip()
        cfg.website = request.POST.get('website', '').strip()
        cfg.anio_lectivo = request.POST.get('anio_lectivo', '2025-2026').strip()
        cfg.mision = request.POST.get('mision', '').strip()
        cfg.vision = request.POST.get('vision', '').strip()
        cfg.save()
        messages.success(request, 'Institución guardada correctamente.')
        return redirect('setup:materias')
    return render(request, 'setup/wizard.html', {**_ctx('institucion'), 'cfg': cfg})


# ─── PASO 2: Materias ─────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_materias(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        tipo = request.POST.get('tipo_materia', 'INSTRUMENTO')
        desc = request.POST.get('description', '').strip()
        if nombre:
            Subject.objects.get_or_create(name=nombre, defaults={'tipo_materia': tipo, 'description': desc})
            messages.success(request, f'Materia "{nombre}" agregada.')
        return redirect('setup:materias')
    materias = Subject.objects.all().order_by('tipo_materia', 'name')
    return render(request, 'setup/wizard.html', {**_ctx('materias'), 'materias': materias})


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_materia(request, pk):
    Subject.objects.filter(pk=pk).delete()
    messages.success(request, 'Materia eliminada.')
    return redirect('setup:materias')


# ─── PASO 3: Tipos de Aporte ─────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_tipos_aporte(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        peso = request.POST.get('peso', '1.0').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        if nombre and codigo:
            try:
                TipoAporte.objects.get_or_create(
                    codigo=codigo,
                    defaults={'nombre': nombre, 'peso': float(peso), 'descripcion': descripcion,
                              'orden': TipoAporte.objects.count()}
                )
                messages.success(request, f'Tipo de aporte "{nombre}" agregado.')
            except Exception as e:
                messages.error(request, f'Error: {e}')
        return redirect('setup:tipos_aporte')
    tipos = TipoAporte.objects.all().order_by('orden', 'nombre')
    return render(request, 'setup/wizard.html', {**_ctx('tipos_aporte'), 'tipos': tipos})


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_tipo_aporte(request, pk):
    TipoAporte.objects.filter(pk=pk).delete()
    messages.success(request, 'Tipo de aporte eliminado.')
    return redirect('setup:tipos_aporte')


# ─── PASO 5: Niveles / Cursos ─────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_niveles(request):
    if request.method == 'POST':
        level = request.POST.get('level', '').strip()
        section = request.POST.get('section', '').strip()
        if level and section:
            GradeLevel.objects.get_or_create(level=level, section=section)
            messages.success(request, f'Nivel {dict(GradeLevel.LEVEL_CHOICES).get(level, level)} — {section} agregado.')
        return redirect('setup:niveles')
    niveles = GradeLevel.objects.all().order_by('level', 'section')
    return render(request, 'setup/wizard.html', {**_ctx('niveles'), 'niveles': niveles,
                  'level_choices': GradeLevel.LEVEL_CHOICES})


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_nivel(request, pk):
    GradeLevel.objects.filter(pk=pk).delete()
    messages.success(request, 'Nivel eliminado.')
    return redirect('setup:niveles')


# ─── PASO 4: Docentes ─────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_docentes(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        cedula = request.POST.get('cedula', '').strip()
        phone = request.POST.get('phone', '').strip()
        especialidad = request.POST.get('specialization', '').strip()
        password = request.POST.get('password', 'Docente2025!').strip()

        if nombre:
            with transaction.atomic():
                from django.contrib.auth.models import User
                usuario, _ = Usuario.objects.get_or_create(
                    email=email or None,
                    defaults={'nombre': nombre, 'rol': 'DOCENTE', 'phone': phone, 'cedula': cedula or None}
                )
                if not hasattr(usuario, 'teacher_profile'):
                    Teacher.objects.create(usuario=usuario, specialization=especialidad)
                # Crear auth.User si no existe
                username = (email.split('@')[0] if email else nombre.lower().replace(' ', '_'))[:30]
                if not User.objects.filter(username=username).exists():
                    u = User.objects.create_user(username=username, password=password, email=email)
                    usuario.auth_user = u
                    usuario.save()
            messages.success(request, f'Docente "{nombre}" registrado. Usuario: {username}')
        return redirect('setup:docentes')

    docentes = Usuario.objects.filter(rol='DOCENTE').select_related('teacher_profile').order_by('nombre')
    return render(request, 'setup/wizard.html', {**_ctx('docentes'), 'docentes': docentes})


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_docente(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk, rol='DOCENTE')
    nombre = usuario.nombre
    if hasattr(usuario, 'auth_user') and usuario.auth_user:
        usuario.auth_user.delete()
    usuario.delete()
    messages.success(request, f'Docente "{nombre}" eliminado.')
    return redirect('setup:docentes')


# ─── PASO 5: Clases ───────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_clases(request):
    if request.method == 'POST':
        nombre = request.POST.get('name', '').strip()
        subject_id = request.POST.get('subject', '')
        nivel_id = request.POST.get('grade_level', '')
        docente_id = request.POST.get('docente_base', '')
        ciclo = request.POST.get('ciclo_lectivo', '2025-2026').strip()

        if nombre and subject_id:
            Clase.objects.create(
                name=nombre,
                subject_id=subject_id or None,
                grade_level_id=nivel_id or None,
                docente_base_id=docente_id or None,
                ciclo_lectivo=ciclo,
                active=True,
            )
            messages.success(request, f'Clase "{nombre}" creada.')
        return redirect('setup:clases')

    clases = Clase.objects.select_related('subject', 'grade_level', 'docente_base').order_by('name')
    subjects = Subject.objects.all().order_by('name')
    niveles = GradeLevel.objects.all().order_by('level', 'section')
    docentes = Usuario.objects.filter(rol='DOCENTE').order_by('nombre')
    cfg = ConfiguracionInstitucion.get()
    return render(request, 'setup/wizard.html', {
        **_ctx('clases'),
        'clases': clases, 'subjects': subjects, 'niveles': niveles,
        'docentes': docentes, 'anio_lectivo': cfg.anio_lectivo,
    })


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_clase(request, pk):
    c = get_object_or_404(Clase, pk=pk)
    nombre = c.name
    c.delete()
    messages.success(request, f'Clase "{nombre}" eliminada.')
    return redirect('setup:clases')


# ─── PASO 6: Estudiantes ──────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_estudiantes(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        cedula = request.POST.get('cedula', '').strip()
        phone = request.POST.get('phone', '').strip()
        parent_name = request.POST.get('parent_name', '').strip()
        parent_phone = request.POST.get('parent_phone', '').strip()
        nivel_id = request.POST.get('grade_level', '')

        if nombre:
            with transaction.atomic():
                from django.contrib.auth.models import User
                usuario = Usuario.objects.create(
                    nombre=nombre, rol='ESTUDIANTE',
                    email=email or None, phone=phone, cedula=cedula or None,
                )
                Student.objects.create(
                    usuario=usuario,
                    parent_name=parent_name, parent_phone=parent_phone,
                    grade_level_id=nivel_id or None,
                )
                username = (email.split('@')[0] if email else nombre.lower().replace(' ', '_'))[:30]
                if not User.objects.filter(username=username).exists():
                    u = User.objects.create_user(username=username, password='Alumno2025!', email=email)
                    usuario.auth_user = u
                    usuario.save()
            messages.success(request, f'Estudiante "{nombre}" registrado.')
        return redirect('setup:estudiantes')

    estudiantes = Student.objects.select_related('usuario', 'grade_level').order_by('usuario__nombre')
    niveles = GradeLevel.objects.all().order_by('level', 'section')
    return render(request, 'setup/wizard.html', {**_ctx('estudiantes'), 'estudiantes': estudiantes, 'niveles': niveles})


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_estudiante(request, pk):
    st = get_object_or_404(Student, pk=pk)
    nombre = st.usuario.nombre
    if hasattr(st.usuario, 'auth_user') and st.usuario.auth_user:
        st.usuario.auth_user.delete()
    st.usuario.delete()
    messages.success(request, f'Estudiante "{nombre}" eliminado.')
    return redirect('setup:estudiantes')


# ─── PASO 7: Matrículas ───────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_matriculas(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('estudiante', '')
        clase_id = request.POST.get('clase', '')
        if usuario_id and clase_id:
            usuario = get_object_or_404(Usuario, pk=usuario_id, rol='ESTUDIANTE')
            clase = get_object_or_404(Clase, pk=clase_id)
            enr, created = Enrollment.objects.get_or_create(
                estudiante=usuario,
                clase=clase,
                defaults={'docente': clase.docente_base}
            )
            if created:
                messages.success(request, f'Matrícula creada: {usuario.nombre} → {clase.name}')
            else:
                messages.warning(request, 'Esa matrícula ya existe.')
        return redirect('setup:matriculas')

    matriculas = Enrollment.objects.select_related(
        'estudiante', 'clase__subject', 'clase__grade_level'
    ).order_by('estudiante__nombre')
    estudiantes = Usuario.objects.filter(rol='ESTUDIANTE').order_by('nombre')
    clases = Clase.objects.select_related('subject', 'grade_level').order_by('name')
    return render(request, 'setup/wizard.html', {
        **_ctx('matriculas'), 'matriculas': matriculas,
        'estudiantes': estudiantes, 'clases': clases,
    })


@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def delete_matricula(request, pk):
    enr = get_object_or_404(Enrollment, pk=pk)
    nombre = f'{enr.estudiante.nombre} → {enr.clase.name}'
    enr.delete()
    messages.success(request, f'Matrícula "{nombre}" eliminada.')
    return redirect('setup:matriculas')


# ─── PASO 8: WhatsApp ─────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff, login_url='/users/login/')
def step_whatsapp(request):
    import os
    wa = ConfiguracionWhatsapp.objects.first()
    if request.method == 'POST':
        nombre = request.POST.get('nombre_instancia', '').strip()
        ciclo = request.POST.get('ciclo_lectivo', '2025-2026').strip()
        activa = request.POST.get('activa') == 'on'
        # También guardamos la URL/Key en el .env via env vars si se proveen
        api_url = request.POST.get('api_url', '').strip()
        api_key = request.POST.get('api_key', '').strip()
        if nombre:
            if wa:
                wa.nombre_instancia = nombre
                wa.ciclo_lectivo = ciclo
                wa.activa = activa
                wa.save()
            else:
                ConfiguracionWhatsapp.objects.create(
                    nombre_instancia=nombre, ciclo_lectivo=ciclo, activa=activa
                )
            messages.success(request, 'Configuración WhatsApp guardada.')
        return redirect('setup:whatsapp')
    api_url = os.environ.get('EVOLUTION_API_URL', '')
    api_key = os.environ.get('EVOLUTION_API_KEY', '')
    return render(request, 'setup/wizard.html', {
        **_ctx('whatsapp'), 'wa': wa, 'api_url': api_url, 'api_key': api_key
    })
