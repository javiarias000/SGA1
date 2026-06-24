import os
import json
from django.core.management.base import BaseCommand
from classes.models import Clase
from teachers.models import Teacher
from subjects.models import Subject

class Command(BaseCommand):
    help = 'Import classes from a JSON file'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Importando Clases ---'))

        # --- Manual Mapping for Data Inconsistencies ---
        # Map teacher names from JSON to canonical full names in DB
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
        
        # Manual Mapping for Subject Names from Horarios JSON to Canonical Names
        subject_name_map = {
            "Acompañamiento Para Pianistas": "Acompañamiento",
            "Agrupacion: Orquesta, Banda, Ensamble De Guitarra O Coro": "Agrupaciones",
            "Capacitacion En Música": "Capacitación en música",
            "Capacitación En Música": "Capacitación en música", # Keeping both variations from JSON
            "Conjunto Instrumental/Vocal O Mixto": "Conjunto instrumental",
            "Coro Mgs.Marco Tocto": "Coro",
            "Creacion Y Arreglos": "Creación y arreglos",
            "Creación Y Arreglos": "Creación y arreglos", # Keeping both variations from JSON
            "Educación Rítmica Audioperceptiva": "Educación rítmica audioperceptiva",
            "Formación Y Orientación": "Formación y orientación",
            "Formación Y Orientación Laboral": "Formación y orientación",
            "Formas Musical": "Formas musicales",
            "Formas Musicales": "Formas musicales", # Keeping both variations from JSON
            "Historia De La Música": "Historia de la música",
            "Informática Aplicada": "Informática aplicada",
            "Informática Aplicada 9O B": "Informática aplicada",
            "Lenguaje Musica": "Lenguaje musical",
            "Lenguaje Musica Mgs.Israel Pérez": "Lenguaje musical",
            "Lenguaje Musica Mgs.Jorge De La Cruz": "Lenguaje musical",
            "Lenguaje Musical": "Lenguaje musical", # Keeping both variations from JSON
            "Orquesta Pedagógica": "Orquesta pedagógica",
            "Piano Complementario": "Complementario",
            "Producción Artístico Musical": "Producción artístico musical",
            "Lenguaje": "Lenguaje musical",
            "Armonía": "Armonía",
            "Coro": "Coro",
            "Audioperceptiva": "Audioperceptiva",
            "Instrumento": "Instrumento Principal",
        }

        file_path = '/usr/src/base_de_datos_json/horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {file_path}'))
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        unique_classes = set()
        for item in data:
            fields = item.get('fields', {})
            teacher_name = fields.get('docente', '').strip()
            subject_name = fields.get('clase', '').strip()

            if teacher_name and subject_name and teacher_name != 'ND':
                # Use the teacher map to get the canonical name
                teacher_name = teacher_name_map.get(teacher_name, teacher_name)
                # Use the subject map to get the canonical name
                subject_name = subject_name_map.get(subject_name, subject_name)
                unique_classes.add((teacher_name, subject_name))


        created_count = 0
        not_found_teachers = set()
        not_found_subjects = set()

        all_teachers = {t.full_name: t for t in Teacher.objects.all()}
        all_subjects = {s.name: s for s in Subject.objects.all()}



            teacher = all_teachers.get(teacher_name)
            
            # --- Lógica de búsqueda de materia mejorada ---
            subject = None
            # 1. Intentar coincidencia exacta (sensible a mayúsculas)
            subject = all_subjects.get(subject_name)
            
            # 2. Si no, intentar coincidencia exacta (insensible a mayúsculas)
            if not subject:
                for db_subject_name, subject_obj in all_subjects.items():
                    if db_subject_name.lower() == subject_name.lower():
                        subject = subject_obj
                        break
            
            # 3. Si no, intentar coincidencia "comienza con" (insensible a mayúsculas)
            if not subject:
                for db_subject_name, subject_obj in all_subjects.items():
                    if db_subject_name.lower().startswith(subject_name.lower()):
                        subject = subject_obj
                        break # Usar la primera coincidencia encontrada
            


            if teacher and subject:
                class_name = subject.name
                clase, created = Clase.objects.get_or_create(
                    teacher=teacher,
                    subject=subject,
                    defaults={'name': class_name}
                )
                if created:
                    created_count += 1
            else:
                if not teacher:
                    not_found_teachers.add(teacher_name)
                if not subject:
                    not_found_subjects.add(subject_name)
        
        for teacher in not_found_teachers:
            self.stdout.write(self.style.WARNING(f"Docente no encontrado para: '{teacher}'"))
        
        for subject in not_found_subjects:
            self.stdout.write(self.style.WARNING(f"Materia no encontrada para: '{subject}'"))

        self.stdout.write(self.style.SUCCESS('--- Fin de la importación ---'))
        self.stdout.write(self.style.SUCCESS(f'Nuevas clases creadas: {created_count}'))
