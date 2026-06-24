"""
Management command: importa datos del conservatorio.db (SQLite del informe-whatsapp)
al PostgreSQL del SGA1.

Migra:
  - docentes → users.Usuario (rol=DOCENTE) + teachers.Teacher
  - cursos   → classes.GradeLevel
  - tutores_cursos → GradeLevel.docente_tutor

Uso:
  python manage.py import_from_conservatorio_db --db /path/to/conservatorio.db
  python manage.py import_from_conservatorio_db --db /path/to/conservatorio.db --dry-run
"""
import sqlite3
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import Usuario
from teachers.models import Teacher
from classes.models import GradeLevel
from subjects.models import Subject


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r'\D', '', str(raw or ''))
    if not digits:
        return None
    if digits.startswith('593'):
        return digits
    if digits.startswith('0'):
        return '593' + digits[1:]
    if len(digits) == 9:
        return '593' + digits
    return digits


def parse_nivel(nivel_str: str) -> str:
    """Convierte 'Básica Superior' → ciclo en GradeLevel."""
    s = (nivel_str or '').lower()
    if 'bachillerato' in s:
        return 'BACHILLERATO'
    if 'superior' in s or 'superior' in s:
        return 'SUPERIOR'
    if 'media' in s:
        return 'MEDIA'
    return 'BASICA'


class Command(BaseCommand):
    help = 'Importa docentes, cursos y tutores desde el conservatorio.db del informe-whatsapp'

    def add_arguments(self, parser):
        parser.add_argument(
            '--db',
            type=str,
            default='/home/javlabs/n8nauto/informe-whatsapp/conservatorio.db',
            help='Ruta al archivo conservatorio.db',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra lo que haría sin modificar la BD',
        )

    def handle(self, *args, **options):
        db_path = options['db']
        dry_run = options['dry_run']

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
        except Exception as e:
            raise CommandError(f'No se puede abrir {db_path}: {e}')

        self.stdout.write(f'\n{"[DRY RUN] " if dry_run else ""}Importando desde {db_path}\n')

        with transaction.atomic():
            # ── 1. Docentes ───────────────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_HEADING('\n--- Docentes ---'))
            docentes_rows = conn.execute('SELECT * FROM docentes ORDER BY nombre').fetchall()
            docente_id_map = {}  # sqlite_id → Usuario.pk

            for row in docentes_rows:
                nombre = (row['nombre'] or '').strip()
                if not nombre:
                    continue

                phone = normalize_phone(row['celular'])
                email_inst = (row['correo_institucional'] or '').strip() or None
                email_pers = (row['correo_personal'] or '').strip() or None

                if dry_run:
                    self.stdout.write(f'  DOCENTE: {nombre} | tel: {phone} | email: {email_inst}')
                    continue

                # Buscar por nombre (case-insensitive)
                usuario = Usuario.objects.filter(nombre__iexact=nombre).first()
                if not usuario:
                    usuario = Usuario.objects.create(
                        nombre=nombre,
                        rol='DOCENTE',
                        phone=phone,
                        email=email_inst or email_pers,
                    )
                    self.stdout.write(f'  + Creado docente: {nombre}')
                else:
                    updated = False
                    if phone and not usuario.phone:
                        usuario.phone = phone
                        updated = True
                    if email_inst and not usuario.email:
                        usuario.email = email_inst
                        updated = True
                    if updated:
                        usuario.save()
                        self.stdout.write(f'  ~ Actualizado: {nombre}')
                    else:
                        self.stdout.write(f'  = Ya existe: {nombre}')

                # Asegura perfil Teacher
                Teacher.objects.get_or_create(
                    usuario=usuario,
                    defaults={'specialization': row['cargo'] or ''},
                )
                docente_id_map[row['id']] = usuario.pk

            # ── 2. Cursos → GradeLevel ────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_HEADING('\n--- Cursos → GradeLevel ---'))
            cursos_rows = conn.execute('SELECT * FROM cursos ORDER BY anio, paralelo').fetchall()
            curso_id_map = {}  # sqlite_id → GradeLevel.pk

            for row in cursos_rows:
                level = str(row['anio'])
                section = (row['paralelo'] or 'A').upper()
                nivel_str = row['nivel'] or 'Básica'
                ciclo = parse_nivel(nivel_str)

                if dry_run:
                    self.stdout.write(f'  CURSO: {row["nombre"]} → level={level} section={section} ciclo={ciclo}')
                    continue

                gl, created = GradeLevel.objects.get_or_create(
                    level=level,
                    section=section,
                    defaults={'ciclo': ciclo},
                )
                if created:
                    self.stdout.write(f'  + Creado GradeLevel: {gl}')
                else:
                    self.stdout.write(f'  = Ya existe: {gl}')

                curso_id_map[row['id']] = gl.pk

            # ── 3. Tutores_cursos → GradeLevel.docente_tutor ─────────────────
            self.stdout.write(self.style.MIGRATE_HEADING('\n--- Tutores-Cursos ---'))
            tc_rows = conn.execute('SELECT * FROM tutores_cursos').fetchall()

            for row in tc_rows:
                curso_sqlite_id = row['curso_id']
                docente_sqlite_id = row['docente_id']

                if dry_run:
                    self.stdout.write(
                        f'  TUTOR: curso_id={curso_sqlite_id} → docente_id={docente_sqlite_id}'
                    )
                    continue

                gl_pk = curso_id_map.get(curso_sqlite_id)
                doc_pk = docente_id_map.get(docente_sqlite_id)
                if not gl_pk or not doc_pk:
                    self.stdout.write(
                        self.style.WARNING(f'  ! Relación inválida: curso={curso_sqlite_id} docente={docente_sqlite_id}')
                    )
                    continue

                try:
                    gl = GradeLevel.objects.get(pk=gl_pk)
                    tutor = Usuario.objects.get(pk=doc_pk)
                    if gl.docente_tutor != tutor:
                        gl.docente_tutor = tutor
                        gl.save(update_fields=['docente_tutor'])
                        self.stdout.write(f'  + Tutor asignado: {tutor.nombre} → {gl}')
                    else:
                        self.stdout.write(f'  = Tutor ya asignado: {tutor.nombre} → {gl}')
                except (GradeLevel.DoesNotExist, Usuario.DoesNotExist) as e:
                    self.stdout.write(self.style.WARNING(f'  ! Error: {e}'))

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\n[DRY RUN] — No se guardaron cambios.\n'))
            else:
                self.stdout.write(self.style.SUCCESS('\n✓ Importación completada.\n'))

        conn.close()
