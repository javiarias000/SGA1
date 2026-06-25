"""
Importación masiva desde Google Sheets o archivos CSV/Excel.
Cada función importa una entidad específica y devuelve (creados, errores).
"""
import re
import io
import csv
import urllib.request
import unicodedata

import pandas as pd
from django.db import transaction
from django.contrib.auth.models import User

from subjects.models import Subject
from classes.models import GradeLevel, Clase, Enrollment, TipoAporte
from users.models import Usuario
from teachers.models import Teacher
from students.models import Student
from informes.models import ConfiguracionWhatsapp


# ── Columnas esperadas por entidad ───────────────────────────────────────────

SCHEMAS = {
    'materias': {
        'cols': ['nombre', 'tipo', 'descripcion'],
        'requeridos': ['nombre'],
        'ejemplo': 'Piano,INSTRUMENTO,Instrumento de teclado\nSolfeo,TEORIA,Lectura musical\nOrquesta,AGRUPACION,',
    },
    'tipos_aporte': {
        'cols': ['nombre', 'codigo', 'peso', 'orden'],
        'requeridos': ['nombre', 'codigo'],
        'ejemplo': 'Trabajo en clase,TRABAJO,1.0,1\nExposición,EXPO,1.5,2\nTranscripción,TRANS,2.0,3',
    },
    'niveles': {
        'cols': ['nivel', 'paralelo'],
        'requeridos': ['nivel', 'paralelo'],
        'ejemplo': '1,A\n1,B\n2,A\n3,A',
    },
    'docentes': {
        'cols': ['nombre', 'cedula', 'email', 'telefono', 'especialidad'],
        'requeridos': ['nombre'],
        'ejemplo': 'García Juan,1234567890,juan@email.com,0987654321,Piano\nPérez María,,maria@email.com,,Solfeo',
    },
    'estudiantes': {
        'cols': ['nombre', 'cedula', 'email', 'nivel', 'paralelo', 'representante', 'telefono_representante'],
        'requeridos': ['nombre'],
        'ejemplo': 'López Ana,0987654321,ana@email.com,1,A,López Rosa,593987000001',
    },
    'clases': {
        'cols': ['nombre', 'materia', 'docente', 'nivel', 'paralelo', 'ciclo'],
        'requeridos': ['nombre', 'materia'],
        'ejemplo': 'Piano I 2025,Piano,García Juan,1,A,2025-2026',
    },
    'matriculas': {
        'cols': ['cedula_estudiante', 'nombre_clase'],
        'requeridos': ['cedula_estudiante', 'nombre_clase'],
        'ejemplo': '0987654321,Piano I 2025\n1234567890,Solfeo I 2025',
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(s):
    """Normaliza texto: minúsculas, sin tildes, sin espacios extra."""
    if not s:
        return ''
    s = str(s).strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace(' ', '_').replace('-', '_')


def _col(row, *keys):
    """Busca una columna normalizando su nombre."""
    for k in keys:
        nk = _norm(k)
        for col in row.keys():
            if _norm(col) == nk:
                v = row[col]
                return str(v).strip() if v is not None and str(v) != 'nan' else ''
    return ''


def sheet_url_to_csv_url(url):
    """Convierte URL de Google Sheets a URL de exportación CSV."""
    m = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if not m:
        raise ValueError('No se pudo extraer el ID del Google Sheet. Verifica el enlace.')
    sheet_id = m.group(1)
    gid_m = re.search(r'[?&]gid=(\d+)', url)
    gid = gid_m.group(1) if gid_m else '0'
    return f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'


def read_source(file_obj=None, url=None):
    """Lee CSV/Excel desde archivo o URL. Devuelve DataFrame."""
    if url:
        csv_url = sheet_url_to_csv_url(url)
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
        except Exception as e:
            raise ValueError(f'Error al acceder al Google Sheet: {e}. Asegúrate de que el sheet sea público o compartido.')
        df = pd.read_csv(io.BytesIO(raw), encoding='utf-8-sig', dtype=str)
    elif file_obj:
        name = getattr(file_obj, 'name', '')
        if name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_obj, dtype=str)
        else:
            raw = file_obj.read()
            df = pd.read_csv(io.BytesIO(raw), encoding='utf-8-sig', dtype=str)
    else:
        raise ValueError('Debes proporcionar un archivo o un enlace de Google Sheets.')

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how='all')
    return df


# ── Importadores ──────────────────────────────────────────────────────────────

def importar_materias(df):
    creados, actualizados, errores = 0, 0, []
    TIPO_MAP = {'instrumento': 'INSTRUMENTO', 'teoria': 'TEORIA',
                'teoria_musical': 'TEORIA', 'agrupacion': 'AGRUPACION'}
    for i, row in df.iterrows():
        nombre = _col(row, 'nombre', 'name', 'materia')
        if not nombre:
            continue
        tipo_raw = _col(row, 'tipo', 'tipo_materia', 'type')
        tipo = TIPO_MAP.get(_norm(tipo_raw), 'INSTRUMENTO')
        desc = _col(row, 'descripcion', 'description', 'desc')
        try:
            _, created = Subject.objects.get_or_create(
                name=nombre,
                defaults={'tipo_materia': tipo, 'description': desc}
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append(f'Fila {i+2}: {e}')
    return creados, actualizados, errores


def importar_tipos_aporte(df):
    creados, actualizados, errores = 0, 0, []
    for i, row in df.iterrows():
        nombre = _col(row, 'nombre', 'name', 'aporte')
        codigo = _col(row, 'codigo', 'code', 'cod')
        if not nombre or not codigo:
            continue
        try:
            peso = float(_col(row, 'peso', 'weight') or '1.0')
            orden = int(_col(row, 'orden', 'order', 'ord') or '0')
        except ValueError:
            peso, orden = 1.0, 0
        try:
            _, created = TipoAporte.objects.get_or_create(
                codigo=codigo.upper(),
                defaults={'nombre': nombre, 'peso': peso, 'orden': orden}
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append(f'Fila {i+2}: {e}')
    return creados, actualizados, errores


def importar_niveles(df):
    creados, actualizados, errores = 0, 0, []
    LEVEL_MAP = {str(v): str(v) for v in range(1, 12)}
    LEVEL_MAP.update({'basica 1': '1', 'básica 1': '1', 'basica 2': '2', 'básica 2': '2',
                      'media 3': '3', 'media 4': '4', 'media 5': '5',
                      'superior 6': '6', 'superior 7': '7', 'superior 8': '8',
                      'superior 9': '9', 'superior 10': '10', 'superior 11': '11',
                      'bachillerato 9': '9', 'bachillerato 10': '10', 'bachillerato 11': '11'})
    for i, row in df.iterrows():
        nivel_raw = _col(row, 'nivel', 'level', 'grado', 'curso')
        paralelo = _col(row, 'paralelo', 'seccion', 'section', 'grupo')
        if not nivel_raw or not paralelo:
            continue
        level = LEVEL_MAP.get(nivel_raw.strip()) or LEVEL_MAP.get(_norm(nivel_raw))
        if not level:
            errores.append(f'Fila {i+2}: nivel "{nivel_raw}" no reconocido (usar 1-11)')
            continue
        try:
            _, created = GradeLevel.objects.get_or_create(level=level, section=paralelo.upper())
            if created:
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append(f'Fila {i+2}: {e}')
    return creados, actualizados, errores


def importar_docentes(df):
    creados, actualizados, errores = 0, 0, []
    for i, row in df.iterrows():
        nombre = _col(row, 'nombre', 'name', 'docente', 'apellido_nombre', 'apellidos_nombres')
        if not nombre:
            continue
        email = _col(row, 'email', 'correo', 'mail') or None
        cedula = _col(row, 'cedula', 'ci', 'identificacion', 'id') or None
        phone = _col(row, 'telefono', 'phone', 'celular', 'movil') or ''
        especialidad = _col(row, 'especialidad', 'specialization', 'instrumento', 'materia_docente') or ''
        password = _col(row, 'password', 'contrasena', 'clave') or 'Docente2025!'

        try:
            with transaction.atomic():
                # Buscar por cédula o email primero
                usuario = None
                if cedula:
                    usuario = Usuario.objects.filter(cedula=cedula).first()
                if not usuario and email:
                    usuario = Usuario.objects.filter(email=email).first()

                if usuario:
                    usuario.nombre = nombre
                    if phone:
                        usuario.phone = phone
                    usuario.save()
                    actualizados += 1
                else:
                    usuario = Usuario.objects.create(
                        nombre=nombre, rol='DOCENTE',
                        email=email, phone=phone, cedula=cedula,
                    )
                    creados += 1

                if not hasattr(usuario, 'teacher_profile'):
                    try:
                        teacher = usuario.teacher_profile
                        if especialidad:
                            teacher.specialization = especialidad
                            teacher.save()
                    except Exception:
                        Teacher.objects.get_or_create(
                            usuario=usuario,
                            defaults={'specialization': especialidad}
                        )
                else:
                    if especialidad:
                        usuario.teacher_profile.specialization = especialidad
                        usuario.teacher_profile.save()

                # Crear auth.User si no existe
                if not usuario.auth_user:
                    base = (cedula or (email.split('@')[0] if email else nombre.lower().replace(' ', '_')))[:28]
                    username = base
                    suffix = 1
                    while User.objects.filter(username=username).exists():
                        username = f'{base}{suffix}'
                        suffix += 1
                    auth_u = User.objects.create_user(
                        username=username, password=password,
                        email=email or '', first_name=nombre.split()[0] if nombre else '',
                    )
                    usuario.auth_user = auth_u
                    usuario.save()
        except Exception as e:
            errores.append(f'Fila {i+2} ({nombre}): {e}')
    return creados, actualizados, errores


def importar_estudiantes(df):
    creados, actualizados, errores = 0, 0, []
    LEVEL_MAP = {str(v): str(v) for v in range(1, 12)}

    for i, row in df.iterrows():
        nombre = _col(row, 'nombre', 'apellido_nombre', 'apellidos_nombres', 'alumno', 'estudiante')
        if not nombre:
            continue
        email = _col(row, 'email', 'correo') or None
        cedula = _col(row, 'cedula', 'ci', 'identificacion') or None
        phone = _col(row, 'telefono', 'celular') or ''
        parent_name = _col(row, 'representante', 'nombre_representante', 'padre', 'madre', 'rep') or ''
        parent_phone = _col(row, 'telefono_representante', 'tel_rep', 'celular_rep', 'whatsapp') or ''
        nivel_raw = _col(row, 'nivel', 'grado', 'curso', 'level') or ''
        paralelo = _col(row, 'paralelo', 'seccion', 'section') or ''

        # Buscar GradeLevel
        grade_level = None
        nivel_str = LEVEL_MAP.get(nivel_raw.strip())
        if nivel_str and paralelo:
            grade_level = GradeLevel.objects.filter(level=nivel_str, section__iexact=paralelo).first()
        elif nivel_str:
            grade_level = GradeLevel.objects.filter(level=nivel_str).first()

        try:
            with transaction.atomic():
                usuario = None
                if cedula:
                    usuario = Usuario.objects.filter(cedula=cedula).first()
                if not usuario and email:
                    usuario = Usuario.objects.filter(email=email).first()

                if usuario:
                    usuario.nombre = nombre
                    usuario.save()
                    student = getattr(usuario, 'student_profile', None) or Student.objects.filter(usuario=usuario).first()
                    if student:
                        if grade_level:
                            student.grade_level = grade_level
                        if parent_name:
                            student.parent_name = parent_name
                        if parent_phone:
                            student.parent_phone = parent_phone
                        student.save()
                    actualizados += 1
                else:
                    usuario = Usuario.objects.create(
                        nombre=nombre, rol='ESTUDIANTE',
                        email=email, phone=phone, cedula=cedula,
                    )
                    Student.objects.create(
                        usuario=usuario,
                        grade_level=grade_level,
                        parent_name=parent_name,
                        parent_phone=parent_phone,
                    )
                    # auth.User
                    base = (cedula or (email.split('@')[0] if email else nombre.lower().replace(' ', '_')))[:28]
                    username = base
                    suffix = 1
                    while User.objects.filter(username=username).exists():
                        username = f'{base}{suffix}'
                        suffix += 1
                    auth_u = User.objects.create_user(
                        username=username, password='Alumno2025!',
                        email=email or '', first_name=nombre.split()[0] if nombre else '',
                    )
                    usuario.auth_user = auth_u
                    usuario.save()
                    creados += 1
        except Exception as e:
            errores.append(f'Fila {i+2} ({nombre}): {e}')
    return creados, actualizados, errores


def importar_clases(df):
    creados, actualizados, errores = 0, 0, []
    LEVEL_MAP = {str(v): str(v) for v in range(1, 12)}

    for i, row in df.iterrows():
        nombre = _col(row, 'nombre', 'clase', 'name')
        materia_str = _col(row, 'materia', 'subject', 'asignatura')
        if not nombre or not materia_str:
            continue

        subject = Subject.objects.filter(name__icontains=materia_str).first()
        if not subject:
            errores.append(f'Fila {i+2}: materia "{materia_str}" no encontrada')
            continue

        docente_str = _col(row, 'docente', 'profesor', 'teacher', 'docente_email')
        docente = None
        if docente_str:
            docente = (Usuario.objects.filter(nombre__icontains=docente_str, rol='DOCENTE').first()
                       or Usuario.objects.filter(email=docente_str, rol='DOCENTE').first())

        nivel_raw = _col(row, 'nivel', 'level', 'grado')
        paralelo = _col(row, 'paralelo', 'seccion', 'section')
        grade_level = None
        nivel_str = LEVEL_MAP.get(nivel_raw.strip())
        if nivel_str and paralelo:
            grade_level = GradeLevel.objects.filter(level=nivel_str, section__iexact=paralelo).first()

        ciclo = _col(row, 'ciclo', 'ciclo_lectivo', 'periodo', 'year') or '2025-2026'

        try:
            _, created = Clase.objects.get_or_create(
                name=nombre,
                defaults={
                    'subject': subject,
                    'grade_level': grade_level,
                    'docente_base': docente,
                    'ciclo_lectivo': ciclo,
                    'active': True,
                }
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append(f'Fila {i+2} ({nombre}): {e}')
    return creados, actualizados, errores


def importar_matriculas(df):
    creados, actualizados, errores = 0, 0, []

    for i, row in df.iterrows():
        cedula = _col(row, 'cedula_estudiante', 'cedula', 'ci_estudiante', 'ci')
        clase_str = _col(row, 'nombre_clase', 'clase', 'class', 'asignatura')

        if not cedula or not clase_str:
            errores.append(f'Fila {i+2}: cedula y nombre_clase son obligatorios')
            continue

        estudiante = Usuario.objects.filter(cedula=cedula, rol='ESTUDIANTE').first()
        if not estudiante:
            errores.append(f'Fila {i+2}: estudiante con cédula {cedula} no encontrado')
            continue

        clase = Clase.objects.filter(name__icontains=clase_str).first()
        if not clase:
            errores.append(f'Fila {i+2}: clase "{clase_str}" no encontrada')
            continue

        try:
            _, created = Enrollment.objects.get_or_create(
                estudiante=estudiante,
                clase=clase,
                defaults={'docente': clase.docente_base}
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append(f'Fila {i+2}: {e}')
    return creados, actualizados, errores


IMPORTADORES = {
    'materias':     importar_materias,
    'tipos_aporte': importar_tipos_aporte,
    'niveles':      importar_niveles,
    'docentes':     importar_docentes,
    'estudiantes':  importar_estudiantes,
    'clases':       importar_clases,
    'matriculas':   importar_matriculas,
}
