import os
import json
from django.core.management.base import BaseCommand
from classes.models import Enrollment, Clase
from students.models import Student
from subjects.models import Subject
from teachers.models import Teacher # <--- Asegúrate de que 'Teacher' está importado si lo usas
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Import enrollments from JSON files'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Importando Matrículas ---'))
        
        # --- Manual Mapping for Data Inconsistencies (from import_classes) ---
        teacher_name_map = {
            "Daniel Laura.": "Laura Guamán Christian Daniel",
            "Marco Paredes": "Paredes Santana Marco Antonio",
            "Inés Larreátegui": "Larreátegui Feijoó Inés María",
            "Daniel Laura": "Laura Guamán Christian Daniel",
            "Elizabeth Reyes": "Reyes Garcés Elizabeth Del Rocío",
            "Delia Núñez": "Nuñez Cunalata Zoila Delia",
            "Jenny Amores": "Amores Valdivieso Jenny Natividad",
            "Diego Túquerez": "Túquerez Núñez Diego Javier",
            "Andrea Peña": "Peña Núñez Andrea Michelle",
            "Guillermo Fonseca": "Fonseca Sandoval Walter Guillermo",
            "Juan Solís": "Solís Solís Juan Francisco",
            "Rafael Guzñay": "Guzñay Paca Inti Rafael",
            "Fabricio Chico": "Chico Analuisa Fabricio Renato",
            "Acosta Karolina": "Acosta Zagal Karolina",
            "Roberto Caiza": "Caiza Caiza Roberto Carlos",
            "Félix Amancha": "Amancha Hidalgo Félix Marcelo",
            "Danny Toapanta": "Toapanta Arequipa Danny Alexander",
            "Juan Diego Gutama": "Gutama Galan Juan Diego",
            "Angel Quinapanta": "Quinapanta Tibán Angel Rodrigo",
            "Jorge Arevalos": "Arevalo Catañeda Angel Jorge",
            "Alex Chicaiza": "Chicaiza Yánez Jefferson Alexander",
            "Christian Peralta": "Peralta Aponte Christian Hernán",
            "Santiago Zumbana": "Zumbana Quinapanta Santiago Maximiliano",
            "Jorge Arias": "Arias Cuenca Jorge Javier",
            "David Vásquez": "Vasquez Sánchez David Hernán",
            "Edwin Chico": "Chico Espinoza Edwin Patricio",
            "Marcelo Chicaiza": "Chicaiza Orozco Marcelo Javier",
            "Santiago Guananga": "Guananga Aizabucha Javier Santiago",
            "Diego Pérez": "Pérez Toapanta Diego Armando",
            "Marco Tocto": "Tocto Villareal Marco Antonio",
            "Jorge De La Cruz": "De La Cruz Changalombo Jorge Ramiro",
            "David Díaz": "Díaz Loyola David Descartes",
            "Mgs.Israel Pérez": "Pérez Mayorga Edwin Israel",
            "Dr. Rubén Chicaiza": "Chicaiza Cuenca Rubén Geovany",
            "Mgs. Mauricio Jiménez": "Jiménez Vega Mauricio Marmonte",
            "Jorge Arevalo": "Arevalo Catañeda Angel Jorge",
            "Mgs.Jorge De La Cruz": "De La Cruz Changalombo Jorge Ramiro",
            "José Luis Cumbicos": "Cumbicos Macas José Luis",
            "Mgs.Marco Tocto": "Tocto Villareal Marco Antonio",
        }
        
        subject_name_map = {
            "Acompañamiento Para Pianistas": "Acompañamiento",
            "Agrupacion: Orquesta, Banda, Ensamble De Guitarra O Coro": "Agrupaciones",
            "Capacitacion En Música": "Capacitación en música",
            "Capacitacion En Música": "Capacitación en música",
            "Conjunto Instrumental/Vocal O Mixto": "Conjunto instrumental",
            "Coro Mgs.Marco Tocto": "Coro",
            "Creacion Y Arreglos": "Creación y arreglos",
            "Creación Y Arreglos": "Creación y arreglos",
            "Educación Rítmica Audioperceptiva": "Educación rítmica audioperceptiva",
            "Formación Y Orientación": "Formación y orientación",
            "Formación Y Orientación Laboral": "Formación y orientación",
            "Formas Musical": "Formas musicales",
            "Formas Musicales": "Formas musicales",
            "Historia De La Música": "Historia de la música",
            "Informática Aplicada": "Informática aplicada",
            "Informática Aplicada 9O B": "Informática aplicada",
            "Lenguaje Musica": "Lenguaje musical",
            "Lenguaje Musica Mgs.Israel Pérez": "Lenguaje musical",
            "Lenguaje Musica Mgs.Jorge De La Cruz": "Lenguaje musical",
            "Lenguaje Musical": "Lenguaje musical",
            "Orquesta Pedagógica": "Orquesta pedagógica",
            "Piano Complementario": "Complementario",
            "Producción Artístico Musical": "Producción artístico musical",
            "Lenguaje": "Lenguaje musical",
            "Armonía": "Armonía",
            "Coro": "Coro",
            "Audioperceptiva": "Audioperceptiva",
            "Instrumento": "Instrumento Principal",
        }
        # --- End of Manual Mapping ---
        
        
        json_base_dir = '/usr/src/base_de_datos_json'
        instrumento_dir = os.path.join(json_base_dir, 'Instrumento_Agrupaciones')
        agrupaciones_dir = os.path.join(json_base_dir, 'asignaciones_grupales')

        created_count = 0
        
        # --- Process Instrumento_Agrupaciones files ---
        if os.path.exists(instrumento_dir):
            for filename in os.listdir(instrumento_dir):
                if filename.endswith('.json') and \
                   filename != 'ESTUDIANTES_CON_REPRESENTANTES.json' and \
                   filename != 'ASIGNACIONES_instrumento_que_estudia_en_el_conservatorio_bolívar.json':
                    
                    file_path = os.path.join(instrumento_dir, filename)
                    self.stdout.write(self.style.NOTICE(f'Procesando archivo: {filename}'))

                    # Extract subject name from filename and canonicalize it
                    raw_subject_name_from_file = filename.replace('ASIGNACIONES_', '').replace('.json', '').replace('_', ' ').strip().capitalize()
                    # Apply the same subject_name_map for consistency
                    canonical_subject_name_from_file = subject_name_map.get(raw_subject_name_from_file, raw_subject_name_from_file)

                    self.stdout.write(f"  DEBUG: filename: {filename}")
                    self.stdout.write(f"  DEBUG: raw_subject_name_from_file: '{raw_subject_name_from_file}'")
                    self.stdout.write(f"  DEBUG: canonical_subject_name_from_file (after map): '{canonical_subject_name_from_file}'")

                    # Robust subject lookup (copied from import_classes.py)
                    subject = None
                    all_subjects = {s.name: s for s in Subject.objects.all()} # Re-fetch to be safe
                    # 1. Try exact match (case-sensitive)
                    subject = all_subjects.get(canonical_subject_name_from_file)
                    
                    # 2. If not, try exact match (case-insensitive)
                    if not subject:
                        for db_subject_name, subject_obj in all_subjects.items():
                            if db_subject_name.lower() == canonical_subject_name_from_file.lower():
                                subject = subject_obj
                                break
                    
                    # 3. If not, try "starts with" match (case-insensitive)
                    if not subject:
                        for db_subject_name, subject_obj in all_subjects.items():
                            if db_subject_name.lower().startswith(canonical_subject_name_from_file.lower()):
                                subject = subject_obj
                                break # Usar la primera coincidencia encontrada
                    
                    self.stdout.write(f"  DEBUG: Subject found in DB: {subject.name if subject else 'None'}")
                    
                    if not subject:
                        self.stdout.write(self.style.WARNING(f"Materia '{canonical_subject_name_from_file}' (del archivo '{filename}') no encontrada en la DB. Omitiendo archivo."))
                        continue

                    
                    # Find classes associated with this subject
                    clases = Clase.objects.filter(subject=subject)
                    if not clases.exists():
                        self.stdout.write(self.style.WARNING(f"No se encontraron clases para la materia '{subject.name}'. Omitiendo archivo {filename}"))
                        continue

                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data:
                        fields = item.get('fields', {})
                        student_full_name_json = fields.get('full_name', '').strip() # Assuming this is student's full name from new JSON
                        docente_nombre_json = fields.get('docente_nombre', '').strip()
                        specialization_instrument_json = fields.get('specialization_instrument', '').strip()

                        if not student_full_name_json or not docente_nombre_json or not specialization_instrument_json:
                            self.stdout.write(self.style.WARNING(f"Registro omitido por datos incompletos en {filename}: {fields}"))
                            continue
                        
                        # Find the student
                        student = Student.objects.filter(name__iexact=student_full_name_json).first()
                        if not student:
                            self.stdout.write(self.style.WARNING(f"Estudiante '{student_full_name_json}' no encontrado. No se pudo matricular."))
                            continue
                        
                        # Apply maps for teacher and subject
                        canonical_teacher_name = teacher_name_map.get(docente_nombre_json, docente_nombre_json)
                        canonical_subject_name = subject_name_map.get(specialization_instrument_json, specialization_instrument_json)

                        self.stdout.write(f"  DEBUG: Processing Agrupaciones - Raw subject: '{specialization_instrument_json}'")
                        self.stdout.write(f"  DEBUG: Processing Agrupaciones - Canonical subject: '{canonical_subject_name}'")

                        # ASUMIMOS que importaste Teacher
                        teacher = Teacher.objects.filter(full_name__iexact=canonical_teacher_name).first() 
                        
                        # Robust subject lookup (copied from import_classes.py)
                        subject = None
                        all_subjects_dict = {s.name: s for s in Subject.objects.all()} # Re-fetch to be safe
                        # 1. Try exact match (case-sensitive)
                        subject = all_subjects_dict.get(canonical_subject_name)
                        
                        # 2. If not, try exact match (case-insensitive)
                        if not subject:
                            for db_subject_name, subject_obj in all_subjects_dict.items():
                                if db_subject_name.lower() == canonical_subject_name.lower():
                                    subject = subject_obj
                                    break
                        
                        # 3. If not, try "starts with" match (case-insensitive)
                        if not subject:
                            for db_subject_name, subject_obj in all_subjects_dict.items():
                                if db_subject_name.lower().startswith(canonical_subject_name.lower()):
                                    subject = subject_obj
                                    break # Usar la primera coincidencia encontrada

                        self.stdout.write(f"  DEBUG: Processing Agrupaciones - Subject found in DB: {subject.name if subject else 'None'}")

                        if not teacher:
                            self.stdout.write(self.style.WARNING(f"Docente '{canonical_teacher_name}' no encontrado para '{student_full_name_json}'. No se pudo matricular."))
                            continue
                        if not subject:
                            self.stdout.write(self.style.WARNING(f"Materia '{canonical_subject_name}' no encontrada para '{student_full_name_json}'. No se pudo matricular."))
                            continue
                        
                        # Construct expected class name (same logic as import_classes)
                        expected_class_name = subject.name
                        
                        # Find the specific Clase object
                        clase = Clase.objects.filter(
                            name__iexact=expected_class_name,
                            teacher=teacher,
                            subject=subject
                        ).first()

                        if not clase:
                            self.stdout.write(self.style.WARNING(f"Clase '{expected_class_name}' no encontrada para '{student_full_name_json}'. No se pudo matricular."))
                            continue
                        
                        try:
                            enrollment, created = Enrollment.objects.get_or_create(
                                student=student,
                                clase=clase,
                                defaults={'active': True}
                            )
                            if created:
                                created_count += 1
                                self.stdout.write(self.style.SUCCESS(f"Matrícula creada: {student.name} en {clase.name}"))
                        except IntegrityError:
                            self.stdout.write(self.style.NOTICE(f"Matrícula existente: {student.name} ya está en {clase.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Directorio no encontrado: {instrumento_dir}"))

        self.stdout.write(self.style.SUCCESS('--- Fin de la importación de Matrículas ---'))
        self.stdout.write(self.style.SUCCESS(f'Total de nuevas matrículas creadas: {created_count}'))