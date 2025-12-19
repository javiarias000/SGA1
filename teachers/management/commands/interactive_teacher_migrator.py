import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from teachers.models import Teacher
from subjects.models import Subject # Assuming Subject is needed for many-to-many

User = get_user_model()

# Helper function (from previous script)
def normalize_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().replace('.', '').strip()
    titles = ["mgs", "lic", "dr", "ing"]
    for title in titles:
        name = name.replace(title + ' ', '')
    return ' '.join(name.split())

class Command(BaseCommand):
    help = 'Migrates teacher data from a JSON file with interactive field mapping.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando el migrador interactivo de docentes...'))

        # --- 1. Get JSON file path and load data ---
        base_json_dir = '/usr/src/base_de_datos_json/personal_docente/'
        file_name_input = input(self.style.NOTICE("Por favor, introduce el NOMBRE del archivo JSON de docentes (ej. DOCENTES.json): "))
        file_path = os.path.join(base_json_dir, file_name_input)

        if not os.path.exists(file_path):
            raise CommandError(f"El archivo no existe en la ruta esperada: '{file_path}'. Asegúrate de que el nombre del archivo sea correcto y que esté en la carpeta 'base_de_datos_json/personal_docente/' de tu proyecto.")
        
        raw_data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            raw_data.append(json.loads(line))
                        except json.JSONDecodeError:
                            raise CommandError(f"Error al decodificar la línea {line_num} del archivo JSON. Línea problemática: '{line}'")
            if not raw_data:
                raise CommandError(f"El archivo '{file_path}' está vacío o no contiene JSON válido.")
        except Exception as e:
            raise CommandError(f"Ocurrió un error al leer o procesar el archivo: {e}")

        self.stdout.write(self.style.SUCCESS(f"\nArchivo '{file_path}' cargado exitosamente. Se encontraron {len(raw_data)} registros."))

        # --- 2. Display sample record and ask for field mappings ---
        sample_record = raw_data[0]
        self.stdout.write(self.style.NOTICE("\nMostrando un registro de ejemplo del archivo JSON:"))
        for key, value in sample_record.items():
            self.stdout.write(f"  '{key}': {value}")

        available_json_fields = list(sample_record.keys())
        self.stdout.write(self.style.NOTICE("\nCampos disponibles en el JSON de ejemplo: " + ", ".join(available_json_fields)))

        # Define fields needed for Django User and Teacher models
        django_fields = {
            "username": {"source": None, "required": True, "description": "Campo para el nombre de usuario (User.username)"},
            "password": {"source": None, "required": True, "description": "Contraseña para el usuario (User.password)"},
            "email": {"source": None, "required": True, "description": "Correo electrónico del usuario (User.email)"},
            "full_name_json": {"source": None, "required": True, "description": "Nombre completo desde el JSON, para dividir en first_name y last_name de User, y Teacher.full_name"},
            "specialization": {"source": None, "required": False, "description": "Especialización del docente (Teacher.specialization)"},
            "phone": {"source": None, "required": False, "description": "Teléfono del docente (Teacher.phone)"},
            "photo": {"source": None, "required": False, "description": "Ruta de la foto del docente (Teacher.photo)"},
            # "subjects" will be handled separately if needed for initial assignment
        }

        self.stdout.write(self.style.NOTICE("\n--- Mapeo Interactivo de Campos ---"))
        self.stdout.write(self.style.NOTICE("Para cada campo de Django, introduce el nombre del campo correspondiente en tu JSON."))
        self.stdout.write(self.style.NOTICE("Opciones especiales: 'omitir' para dejar en blanco (si no es requerido), 'auto' para autogenerar (ej. para password), 'dividir_fullname' (solo para first_name y last_name si full_name_json ya se mapeó)."))

        mappings = {}
        for field, details in django_fields.items():
            while True:
                prompt_text = self.style.NOTICE(f"¿Qué campo de tu JSON corresponde a '{field}' ({details['description']})? ")
                if not details['required']:
                    prompt_text = self.style.NOTICE(f"¿Qué campo de tu JSON corresponde a '{field}' ({details['description']})? (O 'omitir' para dejar en blanco) ")
                
                user_input = input(prompt_text).strip().lower()

                if user_input == 'omitir' and not details['required']:
                    mappings[field] = None
                    break
                elif user_input == 'omitir' and details['required']:
                    self.stdout.write(self.style.WARNING(f"'{field}' es un campo requerido y no puede omitirse. Intenta de nuevo."))
                elif user_input == 'auto' and field == 'password':
                    mappings[field] = 'auto'
                    break
                elif user_input == 'dividir_fullname' and (field == 'first_name' or field == 'last_name'):
                    if 'full_name_json' not in mappings or not mappings['full_name_json']:
                        self.stdout.write(self.style.WARNING("Debes mapear 'full_name_json' primero para poder usar 'dividir_fullname'. Intenta de nuevo."))
                    else:
                        mappings[field] = 'dividir_fullname'
                        break
                elif user_input in available_json_fields:
                    mappings[field] = user_input
                    break
                else:
                    self.stdout.write(self.style.WARNING(f"Campo '{user_input}' no encontrado en tu JSON o es una opción inválida. Intenta de nuevo."))
        
        # --- Handle first_name and last_name from full_name_json if specified ---
        if mappings.get('full_name_json'):
            self.stdout.write(self.style.NOTICE("\n--- Configuración para dividir el nombre completo ---"))
            self.stdout.write(self.style.NOTICE("Identificado que el 'full_name_json' contiene dos apellidos y dos nombres. Ejemplo: 'Apellido1 Apellido2 Nombre1 Nombre2'"))
            self.stdout.write(self.style.NOTICE("Por defecto, se tomará 'Nombre1 Nombre2' para first_name y 'Apellido1 Apellido2' para last_name."))
            self.stdout.write(self.style.NOTICE("Si esta lógica es correcta, puedes usar 'dividir_fullname' para first_name y last_name."))

            if 'first_name' not in mappings or mappings['first_name'] != 'dividir_fullname':
                while True:
                    user_input = input(self.style.NOTICE("¿Quieres usar 'dividir_fullname' para 'first_name'? (s/n): ")).strip().lower()
                    if user_input == 's':
                        mappings['first_name'] = 'dividir_fullname'
                        break
                    elif user_input == 'n':
                        mappings['first_name'] = None # User will have to provide another source or leave blank
                        break
                    else:
                        self.stdout.write(self.style.WARNING("Respuesta inválida. Por favor, usa 's' o 'n'."))

            if 'last_name' not in mappings or mappings['last_name'] != 'dividir_fullname':
                while True:
                    user_input = input(self.style.NOTICE("¿Quieres usar 'dividir_fullname' para 'last_name'? (s/n): ")).strip().lower()
                    if user_input == 's':
                        mappings['last_name'] = 'dividir_fullname'
                        break
                    elif user_input == 'n':
                        mappings['last_name'] = None # User will have to provide another source or leave blank
                        break
                    else:
                        self.stdout.write(self.style.WARNING("Respuesta inválida. Por favor, usa 's' o 'n'."))
        
        # --- 3. Process data and migrate ---
        self.stdout.write(self.style.SUCCESS('\n--- Iniciando la migración de datos de docentes ---'))
        
        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for record in raw_data:
                try:
                    # Extract data based on mappings
                    username = record.get(mappings['username']) if mappings['username'] and mappings['username'] != 'auto' else None
                    if not username:
                        raise CommandError(f"No se pudo obtener el nombre de usuario del registro: {record}")

                    password = record.get(mappings['password']) if mappings['password'] and mappings['password'] != 'auto' else 'Cb2025$' # Default password
                    if mappings['password'] == 'auto':
                        password = 'Cb2025$' # Auto-generate simple default password

                    email = record.get(mappings['email']) if mappings['email'] else ''
                    
                    full_name_from_json = record.get(mappings['full_name_json']) if mappings['full_name_json'] else ''

                    first_name = ''
                    last_name = ''
                    if mappings.get('first_name') == 'dividir_fullname' and full_name_from_json:
                        parts = full_name_from_json.split()
                        if len(parts) >= 4:
                            first_name = f"{parts[2]} {parts[3]}" # Asumiendo "Apellido1 Apellido2 Nombre1 Nombre2"
                        elif len(parts) == 3: # Assuming "Apellido1 Apellido2 Nombre1"
                             first_name = parts[2]
                        elif len(parts) == 2: # Assuming "Nombre1 Nombre2"
                             first_name = f"{parts[0]} {parts[1]}"
                        else:
                             first_name = full_name_from_json # Fallback
                    elif mappings.get('first_name') and mappings['first_name'] != 'dividir_fullname':
                        first_name = record.get(mappings['first_name'], '')
                    
                    if mappings.get('last_name') == 'dividir_fullname' and full_name_from_json:
                        parts = full_name_from_json.split()
                        if len(parts) >= 2:
                            last_name = f"{parts[0]} {parts[1]}" # Asumiendo "Apellido1 Apellido2 Nombre1 Nombre2"
                        elif len(parts) == 1: # Assuming "Apellido1"
                             last_name = parts[0]
                        else:
                             last_name = full_name_from_json # Fallback
                    elif mappings.get('last_name') and mappings['last_name'] != 'dividir_fullname':
                        last_name = record.get(mappings['last_name'], '')
                    
                    # Create or get User
                    user, user_created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'is_staff': True # Ensure teachers are staff
                        }
                    )
                    if user_created:
                        user.set_password(password)
                        user.save()
                        self.stdout.write(self.style.SUCCESS(f"Usuario '{username}' (Django User) creado."))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Usuario '{username}' (Django User) ya existe."))
                    
                    # Create or get Usuario (unified academic user)
                    usuario_instance, usuario_created = Usuario.objects.get_or_create(
                        auth_user=user,
                        defaults={
                            'nombre': teacher_full_name, # Use the full name from JSON
                            'email': email,
                            'rol': Usuario.Rol.DOCENTE,
                            'cedula': '', # Assuming cedula is not in JSON for now
                            'phone': record.get(mappings['phone'], '') if mappings['phone'] else ''
                        }
                    )
                    if usuario_created:
                        self.stdout.write(self.style.SUCCESS(f"Usuario (académico) '{usuario_instance.nombre}' creado."))
                    else:
                        # Update Usuario details if they have changed
                        updated_usuario = False
                        if usuario_instance.nombre != teacher_full_name:
                            usuario_instance.nombre = teacher_full_name
                            updated_usuario = True
                        if usuario_instance.email != email:
                            usuario_instance.email = email
                            updated_usuario = True
                        phone_from_json = record.get(mappings['phone'], '') if mappings['phone'] else ''
                        if usuario_instance.phone != phone_from_json:
                            usuario_instance.phone = phone_from_json
                            updated_usuario = True
                        if updated_usuario:
                            usuario_instance.save()
                            self.stdout.write(self.style.NOTICE(f"Usuario (académico) '{usuario_instance.nombre}' actualizado."))
                        else:
                            self.stdout.write(self.style.NOTICE(f"Usuario (académico) '{usuario_instance.nombre}' ya existe y está actualizado."))

                    # Now get the Teacher profile, which should be created by the signal
                    teacher, teacher_created = Teacher.objects.get_or_create(
                        usuario=usuario_instance,
                        defaults={
                            'specialization': record.get(mappings['specialization'], '') if mappings['specialization'] else '',
                            'photo': record.get(mappings['photo'], '') if mappings['photo'] else ''
                        }
                    )
                    
                    if teacher_created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Docente '{teacher.full_name}' creado y vinculado al usuario académico."))
                    else:
                        # Update existing teacher if specialization or photo are different
                        updated_teacher = False
                        if teacher.specialization != (record.get(mappings['specialization'], '') if mappings['specialization'] else ''):
                            teacher.specialization = (record.get(mappings['specialization'], '') if mappings['specialization'] else '')
                            updated_teacher = True
                        if teacher.photo != (record.get(mappings['photo'], '') if mappings['photo'] else ''):
                            teacher.photo = (record.get(mappings['photo'], '') if mappings['photo'] else '')
                            updated_teacher = True
                        if updated_teacher:
                            teacher.save()
                            updated_count += 1
                            self.stdout.write(self.style.NOTICE(f"Docente '{teacher.full_name}' actualizado."))
                        else:
                            self.stdout.write(self.style.NOTICE(f"Docente '{teacher.full_name}' ya existe y está actualizado."))

                except CommandError as ce:
                    self.stdout.write(self.style.ERROR(f"Error procesando registro {record}: {ce}. Saltando."))
                    skipped_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error inesperado procesando registro {record}: {e}. Saltando."))
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS('\n--- Resumen de la Migración ---'))
        self.stdout.write(self.style.SUCCESS(f"Registros procesados: {len(raw_data)}"))
        self.stdout.write(self.style.SUCCESS(f"Docentes creados: {created_count}"))
        self.stdout.write(self.style.SUCCESS(f"Docentes actualizados: {updated_count}"))
        self.stdout.write(self.style.WARNING(f"Registros saltados por errores: {skipped_count}"))
        self.stdout.write(self.style.SUCCESS('Migración de docentes completada.'))
