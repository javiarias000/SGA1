import re
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from openpyxl import load_workbook
from students.models import Student
from teachers.models import Teacher
from classes.models import Clase, Enrollment
from subjects.models import Subject


def norm(s):
    if s is None:
        return ''
    s = str(s).strip()
    return re.sub(r"\s+", " ", s)


def slug_username(name):
    base = re.sub(r"[^a-z0-9]", "", norm(name).lower()) or "docente"
    candidate = base[:20]
    i = 1
    while User.objects.filter(username=candidate).exists():
        i += 1
        candidate = f"{base[:18]}{i:02d}"
    return candidate


def get_or_create_teacher(full_name):
    full_name = norm(full_name)
    if not full_name:
        full_name = "Docente Sistema"
    teacher = Teacher.objects.filter(full_name__iexact=full_name).first()
    if teacher:
        return teacher
    # Crear usuario base
    username = slug_username(full_name)
    import secrets, string
    rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    user = User.objects.create_user(username=username, password=rand)
    user.first_name = full_name
    user.save()
    teacher = user.teacher_profile
    teacher.full_name = full_name
    teacher.save()
    return teacher


class Command(BaseCommand):
    help = "Importa estudiantes, materias, clases y matrículas desde los archivos de Excel del Conservatorio"

    def add_arguments(self, parser):
        parser.add_argument('--matriculados', default='/Users/javi000/Downloads/25-26 Matriculados Conservatorio Bolívar de AMbato2.xlsx')
        parser.add_argument('--distribucion', default='/Users/javi000/Downloads/25-26 Distribucion instrumento, agrupaciones.xlsx')
        parser.add_argument('--horarios', default='/Users/javi000/Downloads/2025-2026 horarios cursos.xlsx')
        parser.add_argument('--dry-run', action='store_true', help='No guarda cambios, solo muestra resumen')

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts['dry_run']
        created = {"students": 0, "clases": 0, "enrollments": 0, "teachers": 0, "subjects": 0}

        # 1) Importar MATRICULADOS (base principal de estudiantes)
        wb = load_workbook(opts['matriculados'], read_only=True, data_only=True)
        for ws in wb.worksheets:
            if ws.title.strip().lower() == 'total':
                continue
            headers = None
            for row in ws.iter_rows(values_only=True):
                cells = [norm(c) for c in row]
                if not headers:
                    headers = {norm(h).lower(): i for i, h in enumerate(cells)}
                    continue
                if all(not c for c in cells):
                    continue
                ap = cells[headers.get('apellidos del estudiante', -1)] if headers.get('apellidos del estudiante', -1) >= 0 else ''
                no = cells[headers.get('nombres del estudiante', -1)] if headers.get('nombres del estudiante', -1) >= 0 else cells[headers.get('nombres del estudiante ', -1)] if headers and headers.get('nombres del estudiante ', -1) >= 0 else ''
                name = norm(f"{ap} {no}") or cells[headers.get('nombres y apellidos', -1)]
                grade = cells[headers.get('curso', -1)] or ws.title
                paralelo = cells[headers.get('paralelo', -1)]
                if paralelo:
                    grade = f"{grade} {paralelo}"
                parent_email = cells[headers.get('correo electrónico del representante', -1)] or cells[headers.get('dirección de correo electrónico', -1)]
                parent_phone = cells[headers.get('teléfono del representante', -1)] or cells[headers.get('teléfono', -1)]
                instrument_teacher = cells[headers.get('maestro de instrumento', -1)] or cells.get(headers.get('docente instrumento', -1), '') if isinstance(cells, dict) else ''
                if not name:
                    continue
                teacher = get_or_create_teacher(instrument_teacher)
                if teacher.pk and not Teacher.objects.filter(pk=teacher.pk).exists():
                    created['teachers'] += 1
                if not dry:
                    student, _ = Student.objects.get_or_create(
                        teacher=teacher, name=name,
                        defaults={
                            'grade': grade,
                            'parent_email': parent_email,
                            'parent_phone': parent_phone,
                        }
                    )
                created['students'] += 1

        # 2) Importar DISTRIBUCIÓN (clases y agrupaciones)
        wb2 = load_workbook(opts['distribucion'], read_only=True, data_only=True)
        for ws in wb2.worksheets:
            headers = None
            for row in ws.iter_rows(values_only=True):
                cells = [norm(c) for c in row]
                if not headers:
                    headers = {norm(h).lower(): i for i, h in enumerate(cells)}
                    continue
                if all(not c for c in cells):
                    continue
                ap = cells[headers.get('apellidos del estudiante', -1)] if headers.get('apellidos del estudiante', -1) >= 0 else ''
                no = cells[headers.get('nombres del estudiante', -1)] if headers.get('nombres del estudiante', -1) >= 0 else ''
                name = norm(f"{ap} {no}")
                subject_name = cells[headers.get('instrumento que estudia en el conservatorio bolívar', -1)] or cells[headers.get('agrupación', -1)] or ws.title
                teacher_name = cells[headers.get('maestro de instrumento', -1)] or cells[headers.get('docente piano acompañamiento', -1)] or cells[headers.get('docente piano complementario', -1)]
                if not name or not subject_name:
                    continue
                teacher = get_or_create_teacher(teacher_name)
                # Crear/obtener clase por subject+teacher
                if not dry:
                    subject, created_subject = Subject.objects.get_or_create(name=subject_name)
                    if created_subject:
                        created['subjects'] += 1
                    clase, _ = Clase.objects.get_or_create(
                        teacher=teacher,
                        subject=subject,
                        name=f"{subject.name} - {teacher.full_name}",
                        defaults={'active': True}
                    )
                    created['clases'] += 1
                    # Enrolar estudiante si existe
                    student = Student.objects.filter(name__iexact=name).first()
                    if student:
                        Enrollment.objects.get_or_create(student=student, clase=clase)
                        created['enrollments'] += 1

        # 3) (Opcional) Horarios: solo detectar materias adicionales y crear clases vacías por docente genérico
        try:
            wb3 = load_workbook(opts['horarios'], read_only=True, data_only=True)
            subject_hint = set(Subject.objects.values_list('name', flat=True))
            for ws in wb3.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for cell in row:
                        txt = norm(cell)
                        if len(txt) < 4:
                            continue
                        # Heurística: si contiene palabras clave de materias
                        if any(k in txt.lower() for k in ['coro', 'orquesta', 'conjunto', 'guitarra', 'piano', 'armonia', 'teoria']):
                            # extraer palabra capitalizada inicial
                            subj_name = None
                            for key in ['Coro', 'Orquesta', 'Conjunto Instrumental', 'Guitarra Clásica', 'Piano Complementario', 'Piano Acompañamiento']:
                                if key.lower() in txt.lower():
                                    subj_name = key
                                    break
                            if subj_name and subj_name not in subject_hint and not dry:
                                # Crear clase genérica sin docente concreto
                                generic_teacher = get_or_create_teacher('Docente Sistema')
                                subject, created_subject = Subject.objects.get_or_create(name=subj_name)
                                if created_subject:
                                    created['subjects'] += 1
                                Clase.objects.get_or_create(
                                    teacher=generic_teacher, subject=subject, name=subj_name
                                )
                                subject_hint.add(subj_name)
        except Exception:
            pass

        if dry:
            raise CommandError(f"Resumen (dry-run): {created}")
        self.stdout.write(self.style.SUCCESS(f"Importación completada: {created}"))