import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from classes.models import GradeLevel
from users.models import Usuario
from students.models import Student
from subjects.models import Subject
from teachers.models import TeacherSubject, Teacher # Added Teacher import
from utils.etl_normalization import (
    norm_key,
    map_grade_level,
)


class Command(BaseCommand):
    help = 'Interactive data normalization script for students, grade levels, and tutors.'

    def add_arguments(self, parser):
        parser.add_argument('--base-dir', default='base_de_datos_json',
                            help='Base directory containing raw JSON data files.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Perform a dry run without saving changes to the database.')
        parser.add_argument('--auto-confirm', action='store_true',
                            help='Automatically confirm prompts that have a default answer.')

    def handle(self, *args, **options):
        self.base_dir = options['base_dir']
        self.dry_run = options['dry_run']
        self.auto_confirm = options['auto_confirm'] # Store auto_confirm
        self.stdout.write(self.style.SUCCESS(f"Starting interactive normalization (Dry run: {self.dry_run}, Auto-confirm: {self.auto_confirm})..."))

        # Load existing data for interactive matching
        self.grade_levels_by_name: Dict[str, GradeLevel] = {
            norm_key(gl.__str__()): gl for gl in GradeLevel.objects.all()
        }
        self.students_by_norm_name: Dict[str, Student] = {
            norm_key(s.name): s for s in Student.objects.select_related('usuario', 'grade_level').all()
        }
        self.tutors_by_norm_name: Dict[str, Usuario] = {
            norm_key(t.nombre): t for t in Usuario.objects.filter(rol=Usuario.Rol.DOCENTE).all()
        }
        self.subjects_by_norm_name: Dict[str, Subject] = {
            norm_key(s.name): s for s in Subject.objects.all()
        }
        
        self.process_students_and_grade_levels()
        self.process_tutor_assignments()
        self.process_subjects_and_teachers()

        self.stdout.write(self.style.SUCCESS("Interactive normalization complete."))

    def ask_user(self, prompt: str, options: List[str] = None, default: Optional[str] = None) -> str:
        if self.auto_confirm and default is not None:
            return default
            
        while True:
            full_prompt = prompt
            if options:
                full_prompt += f" ({'/'.join(options)})"
            if default is not None:
                full_prompt += f" [Default: {default}]"
            full_prompt += ": "
            
            response = input(full_prompt).strip()
            
            if response == '' and default is not None:
                return default
            
            if options and response not in options:
                self.stdout.write(self.style.ERROR(f"Opción inválida. Por favor, elige una de: {', '.join(options)}"))
                continue
            return response

    def process_students_and_grade_levels(self):
        self.stdout.write(self.style.NOTICE("\n--- Processing Students and Grade Levels ---"))
        # Logic to read student data, identify inconsistencies, and interactively fix them
        # (To be implemented in subsequent steps)
        
        # Placeholder for student data reading
        estudiantes_dir = os.path.join(self.base_dir, 'estudiantes_matriculados')
        if not os.path.exists(estudiantes_dir):
            self.stdout.write(self.style.WARNING(f"Directory not found: {estudiantes_dir}. Skipping student processing."))
            return
        
        for filename in sorted(os.listdir(estudiantes_dir)):
            if not filename.endswith('.json') or 'Total' in filename:
                continue
            
            path = os.path.join(estudiantes_dir, filename)
            self.stdout.write(self.style.NOTICE(f"Processing file: {filename}"))
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                fields = item.get('fields', {})
                raw_full_name = (fields.get('Apellidos') or '').strip() + ' ' + (fields.get('Nombres') or '').strip()
                # Additional fields for Usuario
                raw_email = fields.get('email')
                raw_cedula = fields.get('Número de Cédula del Estudiante')
                raw_phone_cel1 = fields.get('Número telefónico celular 1')
                raw_phone_conv = fields.get('Número telefónico convencional')
                
                # Additional fields for Student
                raw_parent_apellidos = fields.get('Apellidos_Representante')
                raw_parent_nombres = fields.get('Nombres del Representante del Estudiante')
                raw_notes_alergia = str(fields.get('¿Existe alguna alergia/enfermedad/ condición del estudiante que la institución debe tener en cuenta durante clases? Por favor en caso de no existir dejar en blanco esta sección.') or '').strip()
                raw_notes_necesidad = str(fields.get('Si respondió SI Indique cual es la necesidad educativa') or '').strip()

                raw_curso = fields.get('CURSO') or fields.get('Año de estudio')
                raw_paralelo = fields.get('PARALELO')
                
                # Cleaned data for Usuario
                cleaned_email = (raw_email or '').strip()
                if cleaned_email.upper() == 'FALTANTE' or '@' not in cleaned_email:
                    cleaned_email = None
                
                cleaned_cedula = (str(raw_cedula).split('.')[0] if raw_cedula else '').strip()
                if not cleaned_cedula.isdigit():
                    cleaned_cedula = None
                
                cleaned_phone = (str(raw_phone_cel1).split('.')[0] if raw_phone_cel1 else '').strip()
                if not cleaned_phone and raw_phone_conv: # Fallback to conventional phone
                    cleaned_phone = (str(raw_phone_conv).split('.')[0] if raw_phone_conv else '').strip()
                if not cleaned_phone.isdigit():
                    cleaned_phone = None

                # Cleaned data for Student
                cleaned_parent_name = ''
                if raw_parent_apellidos or raw_parent_nombres:
                    cleaned_parent_name = f"{(raw_parent_apellidos or '').strip()} {(raw_parent_nombres or '').strip()}".strip()
                
                cleaned_parent_phone = (str(raw_phone_cel1).split('.')[0] if raw_phone_cel1 else '').strip() # Using same logic for simplicity

                cleaned_notes = []
                if raw_notes_alergia and raw_notes_alergia.lower() not in ['no', 'n/a', '']:
                    cleaned_notes.append(f"Alergia/Enfermedad: {raw_notes_alergia}")
                if raw_notes_necesidad and raw_notes_necesidad.lower() not in ['no', 'n/a', 'none', 'null', '']:
                    cleaned_notes.append(f"Necesidad Educativa: {raw_notes_necesidad}")
                final_notes = "\n".join(cleaned_notes) or ""
                
                if not raw_full_name:
                    continue
                
                self.stdout.write(f"\nStudent: {raw_full_name}")
                
                # 1. Match/Create Usuario and Student
                norm_name = norm_key(raw_full_name)
                student_obj = self.students_by_norm_name.get(norm_name)
                usuario_obj = None

                if student_obj:
                    usuario_obj = student_obj.usuario
                    self.stdout.write(self.style.SUCCESS(f"  -> Matched existing Student: {student_obj.name} (Usuario: {usuario_obj.nombre})"))
                else:
                    self.stdout.write(self.style.WARNING(f"  -> No existing Student/Usuario found for '{raw_full_name}'."))
                    
                    # Try to find a Usuario by name without a Student profile
                    possible_usuarios = Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE)
                    name_parts = raw_full_name.split(' ')
                    if len(name_parts) >= 1:
                        possible_usuarios = possible_usuarios.filter(nombre__icontains=name_parts[0])
                    if len(name_parts) >= 2:
                        possible_usuarios = possible_usuarios.filter(nombre__icontains=name_parts[-1])
                    
                    possible_usuarios = possible_usuarios.exclude(student_profile__isnull=False)
                    if possible_usuarios.exists():
                        self.stdout.write(self.style.NOTICE(f"  -> Found {possible_usuarios.count()} potential existing Usuarios without Student profiles."))
                        for pu in possible_usuarios:
                            choice = self.ask_user(f"    Link '{raw_full_name}' to existing Usuario '{pu.nombre} ({pu.rol})'?", options=['yes', 'no'], default='no')
                            if choice == 'yes':
                                usuario_obj = pu
                                break
                    
                    if not usuario_obj:
                        create_choice = self.ask_user(f"  -> Create new Usuario and Student for '{raw_full_name}'?", options=['yes', 'no'], default='yes')
                        if create_choice == 'yes':
                            with transaction.atomic():
                                if not self.dry_run:
                                    usuario_obj, created_usuario = Usuario.objects.get_or_create(
                                        nombre=raw_full_name,
                                        defaults={
                                            'rol': Usuario.Rol.ESTUDIANTE,
                                            'email': cleaned_email,
                                            'cedula': cleaned_cedula,
                                            'phone': cleaned_phone,
                                        }
                                    )
                                    student_obj, created_student = Student.objects.get_or_create(
                                        usuario=usuario_obj,
                                        defaults={
                                            'parent_name': cleaned_parent_name,
                                            'parent_phone': cleaned_parent_phone,
                                            'notes': final_notes,
                                        }
                                    )
                                    if created_usuario:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Usuario {usuario_obj.nombre}"))
                                    if created_student:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Student profile for {usuario_obj.nombre}"))
                                    self.students_by_norm_name[norm_name] = student_obj # Update cache
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would get_or_create new Usuario and Student for {raw_full_name}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"  -> Skipping student: {raw_full_name}"))
                            continue
                
                if not usuario_obj: # If student_obj still not found/created
                    continue

                # 2. Match/Create GradeLevel
                parsed_gl = map_grade_level(raw_curso or '', raw_paralelo or '')
                current_grade_level = student_obj.grade_level if student_obj else None
                
                self.stdout.write(f"  Raw Grade Level: Curso='{raw_curso}', Paralelo='{raw_paralelo}'")
                self.stdout.write(f"  Parsed Grade Level: Level='{parsed_gl.level}', Section='{parsed_gl.section}'")
                
                if parsed_gl.level and parsed_gl.section:
                    expected_gl_name = f"{parsed_gl.level} '{parsed_gl.section}'"
                    expected_gl_obj = self.grade_levels_by_name.get(norm_key(expected_gl_name))
                    
                    if expected_gl_obj:
                        self.stdout.write(self.style.SUCCESS(f"  -> Matched existing GradeLevel: {expected_gl_obj}"))
                        if not self.dry_run and (student_obj and student_obj.grade_level != expected_gl_obj):
                            student_obj.grade_level = expected_gl_obj
                            student_obj.save(update_fields=['grade_level'])
                            self.stdout.write(self.style.SUCCESS(f"  -> Updated {student_obj.name}'s GradeLevel to {expected_gl_obj}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  -> No existing GradeLevel found for '{expected_gl_name}'."))
                        create_choice = self.ask_user(f"  -> Create new GradeLevel '{parsed_gl.level} {parsed_gl.section}'?", options=['yes', 'no'], default='yes')
                        if create_choice == 'yes':
                            with transaction.atomic():
                                if not self.dry_run:
                                    new_gl, created_gl = GradeLevel.objects.get_or_create(level=parsed_gl.level, section=parsed_gl.section)
                                    if created_gl:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new GradeLevel {new_gl}"))
                                    else:
                                        self.stdout.write(self.style.NOTICE(f"  -> Found existing GradeLevel {new_gl}"))
                                    self.grade_levels_by_name[norm_key(new_gl.__str__())] = new_gl # Update cache
                                    if student_obj and student_obj.grade_level != new_gl:
                                        student_obj.grade_level = new_gl
                                        student_obj.save(update_fields=['grade_level'])
                                    self.stdout.write(self.style.SUCCESS(f"  -> Assigned to {student_obj.name}"))
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would get_or_create new GradeLevel {parsed_gl.level} {parsed_gl.section} and assign to {raw_full_name}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"  -> GradeLevel for {raw_full_name} remains unassigned."))
                elif parsed_gl.level and not parsed_gl.section: # Level found, but section is missing
                    self.stdout.write(self.style.WARNING(f"  -> Grade Level parsed as Level='{parsed_gl.level}', but Section is missing from raw data: Paralelo='{raw_paralelo}'."))
                    manual_section = self.ask_user(f"  -> Enter Section for Level '{parsed_gl.level}' for student '{raw_full_name}' (e.g., 'A', 'B'):", default='A')
                    if manual_section:
                        parsed_gl = map_grade_level(parsed_gl.level, manual_section) # Re-parse with manual section
                        expected_gl_name = f"{parsed_gl.level} '{parsed_gl.section}'"
                        expected_gl_obj = self.grade_levels_by_name.get(norm_key(expected_gl_name))
                        
                        if expected_gl_obj:
                            self.stdout.write(self.style.SUCCESS(f"  -> Matched existing GradeLevel: {expected_gl_obj}"))
                            if not self.dry_run and (student_obj and student_obj.grade_level != expected_gl_obj):
                                student_obj.grade_level = expected_gl_obj
                                student_obj.save(update_fields=['grade_level'])
                                self.stdout.write(self.style.SUCCESS(f"  -> Updated {student_obj.name}'s GradeLevel to {expected_gl_obj}"))
                        else:
                            create_choice = self.ask_user(f"  -> Create new GradeLevel '{parsed_gl.level} {parsed_gl.section}'?", options=['yes', 'no'], default='yes')
                            if create_choice == 'yes':
                                with transaction.atomic():
                                    if not self.dry_run:
                                        new_gl, created_gl = GradeLevel.objects.get_or_create(level=parsed_gl.level, section=parsed_gl.section)
                                        if created_gl:
                                            self.stdout.write(self.style.SUCCESS(f"  -> Created new GradeLevel {new_gl}"))
                                        else:
                                            self.stdout.write(self.style.NOTICE(f"  -> Found existing GradeLevel {new_gl}"))
                                        self.grade_levels_by_name[norm_key(new_gl.__str__())] = new_gl # Update cache
                                        if student_obj and student_obj.grade_level != new_gl:
                                            student_obj.grade_level = new_gl
                                            student_obj.save(update_fields=['grade_level'])
                                        self.stdout.write(self.style.SUCCESS(f"  -> Assigned to {student_obj.name}"))
                                    else:
                                        self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would get_or_create new GradeLevel {parsed_gl.level} {parsed_gl.section} and assign to {raw_full_name}"))
                            else:
                                self.stdout.write(self.style.WARNING(f"  -> GradeLevel for {raw_full_name} remains unassigned."))
                    else:
                        self.stdout.write(self.style.WARNING(f"  -> Skipping GradeLevel assignment for {raw_full_name} due to missing section."))
                else:
                    self.stdout.write(self.style.WARNING(f"  -> Could not parse Grade Level from raw data: Curso='{raw_curso}', Paralelo='{raw_paralelo}'"))
                    # If existing student has a grade_level, ask if it should be removed
                    if student_obj and student_obj.grade_level:
                        remove_choice = self.ask_user(f"  -> Student {student_obj.name} currently has GradeLevel {student_obj.grade_level}. Remove it?", options=['yes', 'no'], default='no')
                        if remove_choice == 'yes':
                            if not self.dry_run:
                                student_obj.grade_level = None
                                student_obj.save(update_fields=['grade_level'])
                                self.stdout.write(self.style.SUCCESS(f"  -> Removed GradeLevel from {student_obj.name}"))
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would remove GradeLevel from {student_obj.name}"))


    def process_tutor_assignments(self):
        self.stdout.write(self.style.NOTICE("\n--- Processing Tutor Assignments for Grade Levels ---"))
        
        # Reload grade levels to ensure new ones are included
        self.grade_levels_by_name = {
            norm_key(gl.__str__()): gl for gl in GradeLevel.objects.all()
        }

        tutor_report_path = os.path.join(self.base_dir, 'personal_docente', 'REPORTE_TUTORES_CURSOS_20251204_165037.json')
        tutor_suggestions: Dict[str, str] = {} # Map GradeLevel string to suggested tutor name
        
        if os.path.exists(tutor_report_path):
            self.stdout.write(self.style.NOTICE(f"Loading tutor assignments from: {tutor_report_path}"))
            with open(tutor_report_path, 'r', encoding='utf-8') as f:
                tutor_data = json.load(f)
            
            for entry in tutor_data:
                fields = entry.get('fields', {})
                raw_curso = fields.get('curso')
                raw_paralelo = fields.get('paralelo')
                raw_tutor_name = fields.get('tutor')

                parsed_gl = map_grade_level(raw_curso or '', raw_paralelo or '')
                if parsed_gl.level and parsed_gl.section and raw_tutor_name:
                    gl_key = norm_key(f"{parsed_gl.level} '{parsed_gl.section}'")
                    tutor_suggestions[gl_key] = raw_tutor_name
        else:
            self.stdout.write(self.style.WARNING(f"Tutor report not found: {tutor_report_path}. Skipping automatic tutor suggestions."))

        for gl_name, grade_level in self.grade_levels_by_name.items():
            self.stdout.write(f"\nGrade Level: {grade_level.__str__()}")
            current_tutor = grade_level.docente_tutor
            
            suggested_tutor_name = tutor_suggestions.get(gl_name)
            suggested_tutor_obj: Optional[Usuario] = None
            if suggested_tutor_name:
                suggested_tutor_obj = self.tutors_by_norm_name.get(norm_key(suggested_tutor_name))
                if suggested_tutor_obj:
                    self.stdout.write(self.style.NOTICE(f"  Suggested Tutor from report: {suggested_tutor_obj.nombre}"))
            
            effective_tutor_obj = None

            if current_tutor:
                self.stdout.write(f"  Current Tutor: {current_tutor.nombre}")
                
                if suggested_tutor_obj and current_tutor != suggested_tutor_obj:
                    choice = self.ask_user(f"  Suggested tutor '{suggested_tutor_obj.nombre}' differs from current '{current_tutor.nombre}'. Change to suggested?", options=['yes', 'no'], default='no')
                    if choice == 'yes':
                        effective_tutor_obj = suggested_tutor_obj
                    else:
                        effective_tutor_obj = current_tutor # Keep current
                else:
                    change_choice = self.ask_user("  Change current tutor?", options=['yes', 'no'], default='no')
                    if change_choice == 'yes':
                        pass # Proceed to interactive selection
                    else:
                        effective_tutor_obj = current_tutor # Keep current
            elif suggested_tutor_obj:
                choice = self.ask_user(f"  Assign suggested tutor '{suggested_tutor_obj.nombre}'?", options=['yes', 'no'], default='yes')
                if choice == 'yes':
                    effective_tutor_obj = suggested_tutor_obj
                else:
                    pass # Proceed to interactive selection
            
            # If a tutor has been determined automatically, or manually kept, save it and continue
            if effective_tutor_obj and effective_tutor_obj != current_tutor:
                if not self.dry_run:
                    grade_level.docente_tutor = effective_tutor_obj
                    grade_level.save(update_fields=['docente_tutor'])
                    self.stdout.write(self.style.SUCCESS(f"  -> Assigned {effective_tutor_obj.nombre} as tutor for {grade_level.__str__()}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would assign {effective_tutor_obj.nombre} as tutor for {grade_level.__str__()}"))
                continue # Move to next GradeLevel

            # If no effective_tutor_obj yet, or user chose to change/interactively assign
            tutor_search_term = self.ask_user("  Enter part of tutor's name to search (leave blank to skip interactive assignment):", default='' if self.auto_confirm else None)
            if not tutor_search_term:
                self.stdout.write("  -> Skipping interactive tutor assignment for this Grade Level.")
                if not current_tutor and not suggested_tutor_obj: # If no tutor at all, and skipped interactive, ask to remove if exists
                     if grade_level.docente_tutor:
                        remove_choice = self.ask_user("  Remove existing tutor (if any)?", options=['yes', 'no'], default='no')
                        if remove_choice == 'yes':
                            if not self.dry_run:
                                grade_level.docente_tutor = None
                                grade_level.save(update_fields=['docente_tutor'])
                                self.stdout.write(self.style.SUCCESS(f"  -> Removed tutor from {grade_level.__str__()}"))
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would remove tutor from {grade_level.__str__()}"))
                continue
            
            matching_tutors = [t for n, t in self.tutors_by_norm_name.items() if norm_key(tutor_search_term) in n]
            
            if matching_tutors:
                self.stdout.write("  Matching Tutors:")
                for i, tutor in enumerate(matching_tutors):
                    self.stdout.write(f"    [{i+1}] {tutor.nombre} ({tutor.rol})")
                
                while True:
                    tutor_choice = self.ask_user("  Select tutor number (or '0' to skip/create new):", default='0')
                    if tutor_choice == '0':
                        effective_tutor_obj = None # User chose to skip interactive part
                        break
                    
                    try:
                        index = int(tutor_choice) - 1
                        if 0 <= index < len(matching_tutors):
                            selected_tutor = matching_tutors[index]
                            effective_tutor_obj = selected_tutor
                            break
                        else:
                            self.stdout.write(self.style.ERROR("  Invalid number. Please try again."))
                    except ValueError:
                        self.stdout.write(self.style.ERROR("  Invalid input. Please enter a number."))
            else:
                self.stdout.write(self.style.WARNING(f"  -> No tutors found matching '{tutor_search_term}'."))
                create_new_tutor = self.ask_user("  Create a new tutor with this name?", options=['yes', 'no'], default='no')
                if create_new_tutor == 'yes':
                    with transaction.atomic():
                        if not self.dry_run:
                            new_tutor_usuario = Usuario.objects.create(nombre=tutor_search_term, rol=Usuario.Rol.DOCENTE)
                            # Update cache
                            self.tutors_by_norm_name[norm_key(new_tutor_usuario.nombre)] = new_tutor_usuario
                            self.stdout.write(self.style.SUCCESS(f"  -> Created new tutor: {new_tutor_usuario.nombre}"))
                            effective_tutor_obj = new_tutor_usuario
                        else:
                            self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create new tutor: {tutor_search_term}"))
                else:
                    self.stdout.write(self.style.WARNING("  -> Skipping tutor assignment for this Grade Level."))

            if effective_tutor_obj and effective_tutor_obj != current_tutor:
                if not self.dry_run:
                    grade_level.docente_tutor = effective_tutor_obj
                    grade_level.save(update_fields=['docente_tutor'])
                    self.stdout.write(self.style.SUCCESS(f"  -> Assigned {effective_tutor_obj.nombre} as tutor for {grade_level.__str__()}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would assign {effective_tutor_obj.nombre} as tutor for {grade_level.__str__()}"))
            elif not effective_tutor_obj and current_tutor: # If explicitly set to None (user skipped interactive, and no suggestion)
                remove_choice = self.ask_user("  Remove existing tutor (if any)?", options=['yes', 'no'], default='no')
                if remove_choice == 'yes':
                    if not self.dry_run:
                        grade_level.docente_tutor = None
                        grade_level.save(update_fields=['docente_tutor'])
                        self.stdout.write(self.style.SUCCESS(f"  -> Removed tutor from {grade_level.__str__()}"))
                    else:
                        self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would remove tutor from {grade_level.__str__()}"))


    def process_subjects_and_teachers(self):
        self.stdout.write(self.style.NOTICE("\n--- Processing Subjects and Teacher Assignments ---"))

        # Process asignaciones_docentes.json for 'AGRUPACION' subjects
        group_assignments_path = os.path.join(self.base_dir, 'asignaciones_grupales', 'asignaciones_docentes.json')
        if os.path.exists(group_assignments_path):
            self.stdout.write(self.style.NOTICE(f"Processing group teacher assignments from: {group_assignments_path}"))
            with open(group_assignments_path, 'r', encoding='utf-8') as f:
                group_teachers_data = json.load(f)
            
            for entry in group_teachers_data:
                raw_subject_name = entry.get('agrupacion')
                raw_teacher_name = entry.get('docente_asignado')

                if not raw_subject_name or not raw_teacher_name:
                    self.stdout.write(self.style.WARNING(f"  Skipping entry due to missing subject or teacher name: {entry}"))
                    continue
                
                self.stdout.write(f"\n  Processing Group Assignment: Subject='{raw_subject_name}', Teacher='{raw_teacher_name}'")
                
                # 1. Find or create Subject
                norm_subject_name = norm_key(raw_subject_name)
                subject_obj = self.subjects_by_norm_name.get(norm_subject_name)
                
                if not subject_obj:
                    self.stdout.write(self.style.WARNING(f"  -> Subject '{raw_subject_name}' not found. Creating..."))
                    create_choice = self.ask_user(f"  -> Create new Subject '{raw_subject_name}' (Tipo: AGRUPACION)?", options=['yes', 'no'], default='yes')
                    if create_choice == 'yes':
                        with transaction.atomic():
                            if not self.dry_run:
                                subject_obj, created = Subject.objects.get_or_create(
                                    name=raw_subject_name,
                                    defaults={'tipo_materia': Subject.TIPO_MATERIA_CHOICES[1][0]} # 'AGRUPACION'
                                )
                                if created:
                                    self.stdout.write(self.style.SUCCESS(f"  -> Created new Subject: {subject_obj.name}"))
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Found existing Subject: {subject_obj.name}"))
                                self.subjects_by_norm_name[norm_subject_name] = subject_obj
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Subject '{raw_subject_name}' (Tipo: AGRUPACION)"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  -> Skipping subject assignment for '{raw_subject_name}'."))
                        continue
                
                if not subject_obj:
                    continue

                # 2. Find or create Teacher (Usuario with DOCENTE role + Teacher profile)
                norm_teacher_name = norm_key(raw_teacher_name)
                teacher_usuario_obj = self.tutors_by_norm_name.get(norm_teacher_name) # tutors_by_norm_name holds DOCENTE Usuarios
                
                if not teacher_usuario_obj:
                    self.stdout.write(self.style.WARNING(f"  -> Teacher '{raw_teacher_name}' not found. Creating Usuario and Teacher profile..."))
                    create_choice = self.ask_user(f"  -> Create new Usuario '{raw_teacher_name}' (Rol: DOCENTE) and Teacher profile?", options=['yes', 'no'], default='yes')
                    if create_choice == 'yes':
                        with transaction.atomic():
                            if not self.dry_run:
                                teacher_usuario_obj, created_usuario = Usuario.objects.get_or_create(
                                    nombre=raw_teacher_name,
                                    defaults={'rol': Usuario.Rol.DOCENTE}
                                )
                                # Ensure a Teacher profile exists for this Usuario
                                teacher_profile, created_profile = Teacher.objects.get_or_create(
                                    usuario=teacher_usuario_obj,
                                    defaults={'specialization': f'Docente de {subject_obj.name}'}
                                )
                                if created_usuario:
                                    self.stdout.write(self.style.SUCCESS(f"  -> Created new Usuario: {teacher_usuario_obj.nombre}"))
                                if created_profile:
                                    self.stdout.write(self.style.SUCCESS(f"  -> Created new Teacher profile for {teacher_usuario_obj.nombre}"))
                                self.tutors_by_norm_name[norm_teacher_name] = teacher_usuario_obj # Update cache
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Usuario '{raw_teacher_name}' (Rol: DOCENTE) and Teacher profile."))
                    else:
                        self.stdout.write(self.style.WARNING(f"  -> Skipping teacher assignment for '{raw_teacher_name}'."))
                        continue
                else:
                    self.stdout.write(self.style.SUCCESS(f"  -> Matched existing Teacher: {teacher_usuario_obj.nombre}"))
                    # Ensure Teacher profile exists
                    if not hasattr(teacher_usuario_obj, 'teacher_profile'):
                        self.stdout.write(self.style.WARNING(f"  -> Usuario '{teacher_usuario_obj.nombre}' has no Teacher profile. Creating..."))
                        with transaction.atomic():
                            if not self.dry_run:
                                teacher_profile, created_profile = Teacher.objects.get_or_create(
                                    usuario=teacher_usuario_obj,
                                    defaults={'specialization': f'Docente de {subject_obj.name}'}
                                )
                                if created_profile:
                                    self.stdout.write(self.style.SUCCESS(f"  -> Created new Teacher profile for {teacher_usuario_obj.nombre}"))
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Teacher profile for {teacher_usuario_obj.nombre}."))
                
                if not teacher_usuario_obj or not hasattr(teacher_usuario_obj, 'teacher_profile'):
                    continue
                
                # 3. Link Teacher to Subject via TeacherSubject
                with transaction.atomic():
                    if not self.dry_run:
                        teacher_subject, created_link = TeacherSubject.objects.get_or_create(
                            teacher=teacher_usuario_obj.teacher_profile,
                            subject=subject_obj
                        )
                        if created_link:
                            self.stdout.write(self.style.SUCCESS(f"  -> Linked Teacher '{teacher_usuario_obj.nombre}' to Subject '{subject_obj.name}'"))
                        else:
                            self.stdout.write(self.style.NOTICE(f"  -> Link already exists between Teacher '{teacher_usuario_obj.nombre}' and Subject '{subject_obj.name}'"))
                    else:
                        self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would link Teacher '{raw_teacher_name}' to Subject '{raw_subject_name}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Group teacher assignments file not found: {group_assignments_path}. Skipping 'AGRUPACION' subject processing."))

        # Process REPORTE_DOCENTES_HORARIOS_0858.json for 'TEORIA' subjects
        schedule_report_path = os.path.join(self.base_dir, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json')
        if os.path.exists(schedule_report_path):
            self.stdout.write(self.style.NOTICE(f"\nProcessing theoretical subject assignments from: {schedule_report_path}"))
            with open(schedule_report_path, 'r', encoding='utf-8') as f:
                schedule_data = json.load(f)
            
            for item in schedule_data:
                fields = item.get('fields', {})
                raw_subject_name = fields.get('clase')
                raw_teacher_names_str = fields.get('docente')

                if not raw_subject_name or not raw_teacher_names_str or raw_teacher_names_str.upper() == 'ND':
                    self.stdout.write(self.style.WARNING(f"  Skipping entry due to missing subject or teacher name: {fields}"))
                    continue
                
                # Handle multiple teachers for a single subject
                raw_teacher_names = [name.strip() for name in raw_teacher_names_str.split(',')]
                
                # 1. Find or create Subject (Type: TEORIA)
                # Check if it might be an existing AGRUPACION subject
                norm_subject_name = norm_key(raw_subject_name)
                subject_obj = self.subjects_by_norm_name.get(norm_subject_name)

                if subject_obj and subject_obj.tipo_materia == Subject.TIPO_MATERIA_CHOICES[1][0]: # If it's already an AGRUPACION
                    self.stdout.write(self.style.NOTICE(f"\n  Found existing AGRUPACION Subject: '{subject_obj.name}'. Assigning teachers."))
                    # Proceed to teacher assignment for this existing subject
                elif subject_obj: # Existing subject, but not AGRUPACION, assume TEORIA
                    self.stdout.write(self.style.SUCCESS(f"\n  Matched existing TEORIA Subject: {subject_obj.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"\n  -> Subject '{raw_subject_name}' not found. Creating as TEORIA..."))
                    create_choice = self.ask_user(f"  -> Create new Subject '{raw_subject_name}' (Tipo: TEORIA)?", options=['yes', 'no'], default='yes')
                    if create_choice == 'yes':
                        with transaction.atomic():
                            if not self.dry_run:
                                subject_obj, created = Subject.objects.get_or_create(
                                    name=raw_subject_name,
                                    defaults={'tipo_materia': Subject.TIPO_MATERIA_CHOICES[0][0]} # 'TEORIA'
                                )
                                if created:
                                    self.stdout.write(self.style.SUCCESS(f"  -> Created new Subject: {subject_obj.name}"))
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Found existing Subject: {subject_obj.name}"))
                                self.subjects_by_norm_name[norm_subject_name] = subject_obj
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Subject '{raw_subject_name}' (Tipo: TEORIA)"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  -> Skipping subject assignment for '{raw_subject_name}'."))
                        continue
                
                if not subject_obj:
                    continue
                
                # 2. Assign multiple teachers to the subject
                for raw_teacher_name in raw_teacher_names:
                    if not raw_teacher_name:
                        continue
                    self.stdout.write(f"  Processing Theoretical Assignment: Subject='{subject_obj.name}', Teacher='{raw_teacher_name}'")

                    norm_teacher_name = norm_key(raw_teacher_name)
                    teacher_usuario_obj = self.tutors_by_norm_name.get(norm_teacher_name)
                    
                    if not teacher_usuario_obj:
                        self.stdout.write(self.style.WARNING(f"  -> Teacher '{raw_teacher_name}' not found. Creating Usuario and Teacher profile..."))
                        create_choice = self.ask_user(f"  -> Create new Usuario '{raw_teacher_name}' (Rol: DOCENTE) and Teacher profile?", options=['yes', 'no'], default='yes')
                        if create_choice == 'yes':
                            with transaction.atomic():
                                if not self.dry_run:
                                    teacher_usuario_obj, created_usuario = Usuario.objects.get_or_create(
                                        nombre=raw_teacher_name,
                                        defaults={'rol': Usuario.Rol.DOCENTE}
                                    )
                                    teacher_profile, created_profile = Teacher.objects.get_or_create(
                                        usuario=teacher_usuario_obj,
                                        defaults={'specialization': f'Docente de {subject_obj.name}'}
                                    )
                                    if created_usuario:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Usuario: {teacher_usuario_obj.nombre}"))
                                    if created_profile:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Teacher profile for {teacher_usuario_obj.nombre}"))
                                    self.tutors_by_norm_name[norm_teacher_name] = teacher_usuario_obj
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Usuario '{raw_teacher_name}' (Rol: DOCENTE) and Teacher profile."))
                        else:
                            self.stdout.write(self.style.WARNING(f"  -> Skipping teacher assignment for '{raw_teacher_name}'."))
                            continue
                    else:
                        self.stdout.write(self.style.SUCCESS(f"  -> Matched existing Teacher: {teacher_usuario_obj.nombre}"))
                        if not hasattr(teacher_usuario_obj, 'teacher_profile'):
                            self.stdout.write(self.style.WARNING(f"  -> Usuario '{teacher_usuario_obj.nombre}' has no Teacher profile. Creating..."))
                            with transaction.atomic():
                                if not self.dry_run:
                                    teacher_profile, created_profile = Teacher.objects.get_or_create(
                                        usuario=teacher_usuario_obj,
                                        defaults={'specialization': f'Docente de {subject_obj.name}'}
                                    )
                                    if created_profile:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Teacher profile for {teacher_usuario_obj.nombre}"))
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Teacher profile for {teacher_usuario_obj.nombre}."))
                    
                    if not teacher_usuario_obj or not hasattr(teacher_usuario_obj, 'teacher_profile'):
                        continue
                    
                    # Link Teacher to Subject via TeacherSubject
                    with transaction.atomic():
                        if not self.dry_run:
                            teacher_subject, created_link = TeacherSubject.objects.get_or_create(
                                teacher=teacher_usuario_obj.teacher_profile,
                                subject=subject_obj
                            )
                            if created_link:
                                self.stdout.write(self.style.SUCCESS(f"  -> Linked Teacher '{teacher_usuario_obj.nombre}' to Subject '{subject_obj.name}'"))
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Link already exists between Teacher '{teacher_usuario_obj.nombre}' and Subject '{subject_obj.name}'"))
                        else:
                            self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would link Teacher '{raw_teacher_name}' to Subject '{raw_subject_name}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Schedule report file not found: {schedule_report_path}. Skipping 'TEORIA' subject processing."))

        # Process Instrumento_Agrupaciones for 'INSTRUMENTO' subjects
        instrument_assignments_dir = os.path.join(self.base_dir, 'Instrumento_Agrupaciones')
        if os.path.exists(instrument_assignments_dir):
            self.stdout.write(self.style.NOTICE(f"\nProcessing instrument teacher assignments from: {instrument_assignments_dir}"))
            for filename in sorted(os.listdir(instrument_assignments_dir)):
                if not filename.endswith('.json'):
                    continue
                
                path = os.path.join(instrument_assignments_dir, filename)
                self.stdout.write(self.style.NOTICE(f"  Processing instrument file: {filename}"))
                
                with open(path, 'r', encoding='utf-8') as f:
                    instrument_data = json.load(f)
                
                for entry in instrument_data:
                    raw_subject_name = entry.get('instrumento') # Instrumento from the data
                    raw_teacher_name = entry.get('Docente instrumento') # Teacher from the data

                    if not raw_subject_name or not raw_teacher_name:
                        # Sometimes the header row is included, skip it
                        if not raw_subject_name and entry.get('instrumento') == 'Instrumento':
                            continue
                        self.stdout.write(self.style.WARNING(f"  Skipping entry due to missing instrument or teacher name: {entry}"))
                        continue

                    self.stdout.write(f"\n  Processing Instrument Assignment: Instrument='{raw_subject_name}', Teacher='{raw_teacher_name}'")
                    
                    # 1. Find or create Subject (Type: INSTRUMENTO)
                    norm_subject_name = norm_key(raw_subject_name)
                    subject_obj = self.subjects_by_norm_name.get(norm_subject_name)
                    
                    if not subject_obj:
                        self.stdout.write(self.style.WARNING(f"  -> Subject '{raw_subject_name}' not found. Creating..."))
                        create_choice = self.ask_user(f"  -> Create new Subject '{raw_subject_name}' (Tipo: INSTRUMENTO)?", options=['yes', 'no'], default='yes')
                        if create_choice == 'yes':
                            with transaction.atomic():
                                if not self.dry_run:
                                    subject_obj, created = Subject.objects.get_or_create(
                                        name=raw_subject_name,
                                        defaults={'tipo_materia': Subject.TIPO_MATERIA_CHOICES[2][0]} # 'INSTRUMENTO'
                                    )
                                    if created:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Subject: {subject_obj.name}"))
                                    else:
                                        self.stdout.write(self.style.NOTICE(f"  -> Found existing Subject: {subject_obj.name}"))
                                    self.subjects_by_norm_name[norm_subject_name] = subject_obj
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Subject '{raw_subject_name}' (Tipo: INSTRUMENTO)"))
                        else:
                            self.stdout.write(self.style.WARNING(f"  -> Skipping subject assignment for '{raw_subject_name}'."))
                            continue
                    
                    if not subject_obj:
                        continue

                    # 2. Find or create Teacher (Usuario with DOCENTE role + Teacher profile)
                    norm_teacher_name = norm_key(raw_teacher_name)
                    teacher_usuario_obj = self.tutors_by_norm_name.get(norm_teacher_name)
                    
                    if not teacher_usuario_obj:
                        self.stdout.write(self.style.WARNING(f"  -> Teacher '{raw_teacher_name}' not found. Creating Usuario and Teacher profile..."))
                        create_choice = self.ask_user(f"  -> Create new Usuario '{raw_teacher_name}' (Rol: DOCENTE) and Teacher profile?", options=['yes', 'no'], default='yes')
                        if create_choice == 'yes':
                            with transaction.atomic():
                                if not self.dry_run:
                                    teacher_usuario_obj, created_usuario = Usuario.objects.get_or_create(
                                        nombre=raw_teacher_name,
                                        defaults={'rol': Usuario.Rol.DOCENTE}
                                    )
                                    # Ensure a Teacher profile exists for this Usuario
                                    teacher_profile, created_profile = Teacher.objects.get_or_create(
                                        usuario=teacher_usuario_obj,
                                        defaults={'specialization': f'Docente de {subject_obj.name}'}
                                    )
                                    if created_usuario:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Usuario: {teacher_usuario_obj.nombre}"))
                                    if created_profile:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Teacher profile for {teacher_usuario_obj.nombre}"))
                                    self.tutors_by_norm_name[norm_teacher_name] = teacher_usuario_obj # Update cache
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Usuario '{raw_teacher_name}' (Rol: DOCENTE) and Teacher profile."))
                        else:
                            self.stdout.write(self.style.WARNING(f"  -> Skipping teacher assignment for '{raw_teacher_name}'."))
                            continue
                    else:
                        self.stdout.write(self.style.SUCCESS(f"  -> Matched existing Teacher: {teacher_usuario_obj.nombre}"))
                        # Ensure Teacher profile exists
                        if not hasattr(teacher_usuario_obj, 'teacher_profile'):
                            self.stdout.write(self.style.WARNING(f"  -> Usuario '{teacher_usuario_obj.nombre}' has no Teacher profile. Creating..."))
                            with transaction.atomic():
                                if not self.dry_run:
                                    teacher_profile, created_profile = Teacher.objects.get_or_create(
                                        usuario=teacher_usuario_obj,
                                        defaults={'specialization': f'Docente de {subject_obj.name}'}
                                    )
                                    if created_profile:
                                        self.stdout.write(self.style.SUCCESS(f"  -> Created new Teacher profile for {teacher_usuario_obj.nombre}"))
                                else:
                                    self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would create Teacher profile for {teacher_usuario_obj.nombre}."))
                    
                    if not teacher_usuario_obj or not hasattr(teacher_usuario_obj, 'teacher_profile'):
                        continue
                    
                    # 3. Link Teacher to Subject via TeacherSubject
                    with transaction.atomic():
                        if not self.dry_run:
                            teacher_subject, created_link = TeacherSubject.objects.get_or_create(
                                teacher=teacher_usuario_obj.teacher_profile,
                                subject=subject_obj
                            )
                            if created_link:
                                self.stdout.write(self.style.SUCCESS(f"  -> Linked Teacher '{teacher_usuario_obj.nombre}' to Subject '{subject_obj.name}'"))
                            else:
                                self.stdout.write(self.style.NOTICE(f"  -> Link already exists between Teacher '{teacher_usuario_obj.nombre}' and Subject '{subject_obj.name}'"))
                        else:
                            self.stdout.write(self.style.NOTICE(f"  -> Dry run: Would link Teacher '{raw_teacher_name}' to Subject '{raw_subject_name}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Instrument assignments directory not found: {instrument_assignments_dir}. Skipping 'INSTRUMENTO' subject processing."))


