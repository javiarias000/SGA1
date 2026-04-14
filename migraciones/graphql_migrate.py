# Conditional Django setup to prevent re-setup errors when called from manage.py
import os
import json
import requests
import glob
import sys

# print("Script started!") # Removed this line

try:
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_registry.settings')
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        import django
        django.setup()

    from subjects.models import Subject
    from users.models import Usuario
    from teachers.models import Teacher
    from classes.models import GradeLevel
    from classes.models import Clase 
    from utils.etl_normalization import (
        canonical_subject_name,
        canonical_teacher_name,
        canonical_student_name,
        map_grade_level,
        norm_key,
    )
except Exception as e:
    print(f"FATAL ERROR during Django setup or model imports: {e}")
    sys.exit(1)

GRAPHQL_ENDPOINT = "http://web:8000/graphql/"
DB_MAPPINGS_FILE = os.path.join(os.path.dirname(__file__), 'db_mappings.json')

def load_db_mappings():
    if os.path.exists(DB_MAPPINGS_FILE):
        with open(DB_MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "teacher_name_to_id": {},
        "student_name_to_id": {},
        "subject_name_to_info": {},
        "clase_id_map": {},
        "student_pk_to_new_id": {},
        "teacher_pk_to_new_id": {},
        "clase_pk_to_new_id": {}
    }

def save_db_mappings(db_mappings):
    with open(DB_MAPPINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(db_mappings, f, ensure_ascii=False, indent=2)

def execute_graphql_query(query, variables=None):
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "variables": variables if variables else {}
    }
    try:
        response = requests.post(GRAPHQL_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Network error during GraphQL query: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        raise

def import_subjects_graphql(json_path, db_mappings):
    if not os.path.exists(json_path):
        print(f'JSON file not found at {json_path}')
        return {{}}

    unique_subjects = set()
    subject_name_to_info = db_mappings.get("subject_name_to_info", {})
    # This map will store canonical_name -> new_db_id for current run's lookups
    subject_simple_id_map = {name: info["id"] for name, info in subject_name_to_info.items()} if subject_name_to_info else {}

    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f'Expected a list of objects in {json_path}')
        else:
            print(f'Extracting unique subjects from {json_path}...')
            for entry in data:
                instrumento = entry.get('instrumento')
                if instrumento:
                    unique_subjects.add(canonical_subject_name(instrumento))
                agrupacion = entry.get('agrupacion')
                if agrupacion:
                    unique_subjects.add(canonical_subject_name(agrupacion))

    subject_name_to_info_canonical = {}
    for raw_subject_name, info in db_mappings.get('subject_name_to_info', {}).items():
        canonical_name = canonical_subject_name(raw_subject_name)
        subject_name_to_info_canonical[canonical_name] = info
        unique_subjects.add(canonical_name)

    print(f'Importing subjects via GraphQL...')
    created_count = 0
    updated_count = 0

    for subject_name in unique_subjects:
        if not subject_name or subject_name in subject_simple_id_map:
            continue
        
        mutation = """
            mutation CreateSubject($name: String!, $description: String, $tipoMateria: String) {
                createSubject(name: $name, description: $description, tipoMateria: $tipoMateria) {
                    subject {
                        id
                        name
                    }
                }
            }
        """
        tipo_materia = subject_name_to_info_canonical.get(subject_name, {{}}).get('tipo_materia', "OTRO")
        variables = {{"name": subject_name, "description": f'Materia importada: {{subject_name}}', "tipoMateria": tipo_materia}}
        try:
            result = execute_graphql_query(mutation, variables)
            if 'errors' in result:
                error_message = str(result['errors'])
                if 'unique constraint' in error_message or 'duplicate key value' in error_message:
                    try:
                        existing_subject = Subject.objects.get(name=subject_name)
                        subject_simple_id_map[subject_name] = existing_subject.id
                        # Update the full info in db_mappings as well
                        subject_name_to_info[subject_name] = {{"id": existing_subject.id, "tipo_materia": tipo_materia}}
                        updated_count += 1
                        print(f'Subject already exists (via Django ORM): {{subject_name}} (ID: {{existing_subject.id}})')
                    except Subject.DoesNotExist:
                        print(f'Error creating subject {subject_name}: {result["errors"]} (and could not find existing via Django ORM)')
                else:
                    print(f'Error creating subject {{subject_name}}: {{result["errors"]}}')
            else:
                subject_id = result['data']['createSubject']['subject']['id']
                subject_simple_id_map[subject_name] = subject_id
                # Update the full info in db_mappings
                subject_name_to_info[subject_name] = {{"id": subject_id, "tipo_materia": tipo_materia}}
                created_count += 1
                print(f'Created subject (via GraphQL): {{subject_name}} (ID: {{subject_id}})')
        except Exception as e:
            print(f'Error processing subject {{subject_name}}: {{e}}')

    db_mappings["subject_name_to_info"] = subject_name_to_info
    print(f'Finished importing subjects. Created: {{created_count}}, Existing: {{updated_count}}')
    return subject_simple_id_map # Return the simple map for class lookup


def import_teachers_graphql(json_path, db_mappings):
    if not os.path.exists(json_path):
        print(f'JSON file not found at {json_path}')
        return

    data = []
    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f'Error decoding JSON line from {json_path}: {{line}} - {{e}}')
                    continue

    print(f'Importing teachers via GraphQL...')
    updated_usuario_count = 0
    teacher_pk_to_new_id = db_mappings.get("teacher_pk_to_new_id", {{}})

    for entry in data:
        raw_full_name = entry.get('full_name')
        if not raw_full_name:
            print(f'Skipping entry due to missing "full_name": {{entry}}')
            continue
        
        cleaned_name = canonical_teacher_name(raw_full_name)
        if not cleaned_name:
            print(f'Skipping entry for "{{raw_full_name}}" due to empty cleaned name.')
            continue

        cedula_value = str(entry.get('cedula')) if entry.get('cedula') else None
        email_value = entry.get('email')

        mutation = """
            mutation CreateOrUpdateUsuarioTeacher(
                $nombre: String!,
                $email: String,
                $phone: String,
                $cedula: String,
                $specialization: String
            ) {
                createOrUpdateUsuarioTeacher(
                    nombre: $nombre,
                    email: $email,
                    phone: $phone,
                    cedula: $cedula,
                    specialization: $specialization
                ) {
                    usuario {
                        id
                        nombre
                        rol
                        email
                    }
                    teacher {
                        id
                        specialization
                    }
                }
            }
        """
        variables = {
            "nombre": cleaned_name,
            "email": email_value,
            "phone": str(entry.get('phone')) if entry.get('phone') else None,
            "cedula": cedula_value,
            "specialization": str(entry.get('especialidad')) if entry.get('especialidad') else None
        }
        
        try:
            result = execute_graphql_query(mutation, variables)
            if 'errors' in result:
                print(f'Error importing teacher {{cleaned_name}}: {{result["errors"]}}')
            else:
                usuario_data = result['data']['createOrUpdateUsuarioTeacher']['usuario']
                
                if cedula_value:
                    teacher_pk_to_new_id[cedula_value] = usuario_data['id']
                
                updated_usuario_count += 1
                print(f'Upserted teacher (via GraphQL): {{usuario_data["nombre"]}} (ID: {{usuario_data["id"]}})')

        except Exception as e:
            print(f'Error processing teacher {{cleaned_name}}: {{e}}')

    db_mappings["teacher_pk_to_new_id"] = teacher_pk_to_new_id
    print(f'Finished importing teachers. Users upserted: {{updated_usuario_count}}')


def import_gradelevels_graphql(path_pattern):
    json_files = glob.glob(path_pattern)
    if not json_files:
        print(f'No JSON files found matching pattern: {path_pattern}')
        return

    print(f'Extracting unique grade levels from files matching {path_pattern}...')
    unique_grade_levels = set() 
    
    for json_path in json_files:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f'Error decoding JSON from {json_path}: {{e}}')
            continue
        except FileNotFoundError:
            print(f'File not found: {json_path}')
            continue

        if not isinstance(data, list):
            print(f'Expected a list of objects in {json_path}, skipping.')
            continue

        for entry in data:
            fields = entry.get('fields', {})
            curso_raw = fields.get('CURSO')
            paralelo_raw = fields.get('PARALELO')
            
            parsed_grade_level = map_grade_level(curso_raw, paralelo_raw)
            
            if parsed_grade_level.level and parsed_grade_level.section:
                unique_grade_levels.add((parsed_grade_level.level, parsed_grade_level.section))
            elif curso_raw and paralelo_raw:
                print(f'Could not map grade level from "{{curso_raw}}" and "{{paralelo_raw}}" in {json_path}.')


    print(f'Importing grade levels via GraphQL...')
    created_count = 0
    updated_count = 0

    for level, section in unique_grade_levels:
        mutation = """
            mutation CreateGradeLevel($level: String!, $section: String!) {
                createGradeLevel(level: $level, section: $section) {
                    gradeLevel {
                        id
                        level
                        section
                    }
                }
            }
        """
        variables = {{"level": level, "section": section}}
        try:
            result = execute_graphql_query(mutation, variables)
            if 'errors' in result:
                error_message = str(result['errors'])
                if 'unique_together constraint' in error_message or 'duplicate key value violates unique constraint' in error_message:
                    updated_count += 1
                    print(f'GradeLevel already exists (via GraphQL): {{level}} "{{section}}"')
                else:
                    print(f'Error creating GradeLevel {{level}} "{{section}}": {{result["errors"]}}')
            else:
                created_count += 1
                print(f'Created GradeLevel (via GraphQL): {{level}} "{{section}}"')
        except Exception as e:
            print(f'Error processing GradeLevel {{level}} "{{section}}": {{e}}')
    
    print(f'Finished importing grade levels. Created: {{created_count}}, Existing: {{updated_count}}')


def import_students_graphql(path_pattern, db_mappings):
    json_files = glob.glob(path_pattern)
    if not json_files:
        print(f'No JSON files found matching pattern: {path_pattern}')
        return

    print(f'Importing students via GraphQL...')
    updated_usuario_count = 0
    student_pk_to_new_id = db_mappings.get("student_pk_to_new_id", {{}})

    for json_path in json_files:
        print(f'Processing file: {json_path}')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f'Error decoding JSON from {json_path}: {{e}}')
            continue
        except FileNotFoundError:
            print(f'File not found: {json_path}')
            continue

        if not isinstance(data, list):
            print(f'Expected a list of objects in {json_path}, skipping.')
            continue

        for entry in data:
            fields = entry.get('fields', {})
            old_pk = entry.get('pk')
            
            raw_student_name = fields.get('Apellidos', '') + ' ' + fields.get('Nombres', '')
            if not raw_student_name.strip():
                print(f'Skipping entry due to missing student name in {json_path}: {{entry}}')
                continue
            
            cleaned_student_name = canonical_student_name(raw_student_name)
            if not cleaned_student_name:
                print(f'Skipping entry for "{{raw_student_name}}" due to empty cleaned name in {json_path}.')
                continue

            cedula_value = str(fields.get('Número de Cédula del Estudiante')) if fields.get('Número de Cédula del Estudiante') else None
            email_value = fields.get('email')

            curso_raw = fields.get('CURSO')
            paralelo_raw = fields.get('PARALELO')
            grade_level_id = None
            if curso_raw and paralelo_raw:
                parsed_grade_level = map_grade_level(curso_raw, paralelo_raw)
                if parsed_grade_level.level and parsed_grade_level.section:
                    query_grade_level = """
                        query GradeLevelByLevelSection($level: String!, $section: String!) {
                            allGradeLevels(level: $level, section: $section) {
                                id
                            }
                        }
                    """
                    query_vars = {{"level": parsed_grade_level.level, "section": parsed_grade_level.section}}
                    try:
                        gl_result = execute_graphql_query(query_grade_level, query_vars)
                        if gl_result.get('data', {{}}).get('allGradeLevels'):
                            grade_level_id = gl_result['data']['allGradeLevels'][0]['id']
                        else:
                            print(f'Warning: GradeLevel not found for {{parsed_grade_level.level}} "{{parsed_grade_level.section}}". Student {{cleaned_student_name}} will not have a grade level assigned.')
                    except Exception as e:
                        print(f'Error querying GradeLevel for student {{cleaned_student_name}}: {{e}}')
            
            mutation = """
                mutation CreateOrUpdateUsuarioStudent(
                    $nombre: String!,
                    $email: String,
                    $phone: String,
                    $cedula: String,
                    $gradeLevelId: ID,
                    $parentName: String,
                    $parentPhone: String
                ) {
                    createOrUpdateUsuarioStudent(
                        nombre: $nombre,
                        email: $email,
                        phone: $phone,
                        cedula: $cedula,
                        gradeLevelId: $gradeLevelId,
                        parentName: $parentName,
                        parentPhone: $parentPhone
                    ) {
                        usuario {
                            id
                            nombre
                            rol
                        }
                        student {
                            id
                            gradeLevel {
                                id
                            }
                        }
                    }
                }
            """
            variables = {
                "nombre": cleaned_student_name,
                "email": email_value,
                "phone": str(fields.get('Número de cédula del Representante')) if fields.get('Número de cédula del Estudiante') else None,
                "cedula": cedula_value,
                "gradeLevelId": grade_level_id,
                "parentName": f"{str(fields.get('Apellidos del Representante del Estudiante', ''))} {str(fields.get('Nombres del Representante del Estudiante', ''))}".strip() if fields.get('Apellidos del Representante del Estudiante') or fields.get('Nombres del Representante del Estudiante') else None,
                "parentPhone": str(fields.get('Número de cédula del Representante')) if fields.get('Número de cédula del Representante') else None,
            }

            try:
                result = execute_graphql_query(mutation, variables)
                if 'errors' in result:
                    print(f'Error importing student {{cleaned_student_name}}: {{result["errors"]}}')
                else:
                    usuario_data = result['data']['createOrUpdateUsuarioStudent']['usuario']
                    
                    if old_pk:
                        student_pk_to_new_id[str(old_pk)] = usuario_data['id']

                    updated_usuario_count += 1
                    print(f'Upserted student (via GraphQL): {{usuario_data["nombre"]}} (ID: {{usuario_data["id"]}})')

            except Exception as e:
                print(f'Error processing student {{cleaned_student_name}}: {{e}}')
    
    db_mappings["student_pk_to_new_id"] = student_pk_to_new_id
    print(f'Finished importing students. Users upserted: {{updated_usuario_count}}')


def resolve_subject_id_for_clase(canonical_clase_name, db_mappings):
    """Resolve a Subject ID for a given canonical class name.

    First try a direct match against subject_name_to_info (which already
    uses canonical names). If that fails, fall back to a fuzzy match using
    norm_key() so that generic names like "Coro" can be mapped to more
    specific subjects such as "Coro Matutino" / "Coro Vespertino" when
    those exist.
    """
    if not canonical_clase_name:
        return None, None

    subject_name_to_info = db_mappings.get("subject_name_to_info", {{}})

    # 1) Direct match on canonical display name
    direct_info = subject_name_to_info.get(canonical_clase_name)
    if direct_info:
        return direct_info["id"], canonical_clase_name

    # 2) Fuzzy match using normalized keys
    target_norm = norm_key(canonical_clase_name)
    best_candidate = None  # (subject_name, subject_id)

    for subject_name, info in subject_name_to_info.items():
        subj_norm = norm_key(subject_name)

        # Exact normalized match (case/accents/spacing differences only)
        if subj_norm == target_norm:
            return info["id"], subject_name

        # Keyword-based fallback: allow "coro" to match "coro matutino",
        # or vice versa, based on containment of the normalized tokens.
        if target_norm in subj_norm or subj_norm in target_norm:
            # Prefer the most specific match (longest subject_name)
            if not best_candidate or len(subject_name) > len(best_candidate[0]):
                best_candidate = (subject_name, info["id"])

    if best_candidate:
        return best_candidate[1], best_candidate[0]

    return None, None


def import_clases_graphql(json_path, db_mappings):
    print("\n--- Importing Clases ---")
    if not os.path.exists(json_path):
        print(f'JSON file not found at {json_path}')
        return

    teacher_name_to_id = db_mappings.get('teacher_name_to_id', {{}})
    clase_pk_to_new_id = db_mappings.get("clase_pk_to_new_id", {{}})

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f'Expected a list of objects in {json_path}, skipping.')
        return

    created_count = 0
    
    processed_classes = set() 

    for entry in data:
        fields = entry.get('fields', {{}})
        
        clase_name_raw = fields.get('clase')
        docente_name_raw = fields.get('docente')
        curso_raw = fields.get('curso')
        paralelo_raw = fields.get('paralelo')
        aula_raw = fields.get('aula')
        
        if not clase_name_raw or not docente_name_raw:
            continue
        
        canonical_clase_name = canonical_subject_name(clase_name_raw)
        subject_id, matched_subject_name = resolve_subject_id_for_clase(canonical_clase_name, db_mappings)

        if not subject_id:
            print(f'Warning: Subject ID not found for class "{{clase_name_raw}}" (canonical: "{{canonical_clase_name}}"). Skipping class.')
            continue
        
        if matched_subject_name != canonical_clase_name:
            print(
                f'Info: Fallback mapped class "{{clase_name_raw}}" '
                f'(canonical: "{{canonical_clase_name}}") to subject "{{matched_subject_name}}" '
                f'(ID: {{subject_id}}).'
            )

        docente_base_id = None
        docente_id = teacher_name_to_id.get(canonical_teacher_name(docente_name_raw))
        if docente_id:
            docente_base_id = str(docente_id)
        
        if not docente_base_id:
            print(f'Warning: Teacher ID not found for teacher "{{docente_name_raw}}" (canonical: "{{canonical_teacher_name(docente_name_raw)}}"). Class "{{clase_name_raw}}" will be created without a base teacher.')
            
        grade_level_id = None
        if curso_raw and paralelo_raw:
            parsed_grade_level = map_grade_level(curso_raw, paralelo_raw)
            if parsed_grade_level.level and parsed_grade_level.section:
                query_grade_level = """
                    query GradeLevelByLevelSection($level: String!, $section: String!) {
                        allGradeLevels(level: $level, section: $section) {
                            id
                        }
                    }
                """
                query_vars = {{"level": parsed_grade_level.level, "section": parsed_grade_level.section}}
                try:
                    gl_result = execute_graphql_query(query_grade_level, query_vars)
                    if gl_result['data']['allGradeLevels']:
                        grade_level_id = gl_result['data']['allGradeLevels'][0]['id']
                    else:
                        print(f'Warning: GradeLevel not found for {{parsed_grade_level.level}} "{{parsed_grade_level.section}}". Class "{{clase_name_raw}}" will not have a grade level assigned.')
                except Exception as e:
                    print(f'Error querying GradeLevel for class "{{clase_name_raw}}": {{e}}')
        
        ciclo_lectivo = "2025-2026"

        clase_mapping_key = f"{clase_name_raw}|{{subject_id}}|{{ciclo_lectivo}}|{{docente_base_id or 'NONE'}}|{{grade_level_id or 'NONE'}}"

        if clase_mapping_key in processed_classes:
            print(f'Skipping duplicate class entry for: {{clase_name_raw}} - {{docente_name_raw}}')
            continue
        processed_classes.add(clase_mapping_key)

        mutation = """
            mutation CreateClase(
                $name: String!,
                $subjectId: ID!,
                $cicloLectivo: String!,
                $docenteBaseId: ID
            ) {
                createClase(
                    name: $name, 
                    subjectId: $subjectId, 
                    cicloLectivo: $cicloLectivo, 
                    docenteBaseId: $docenteBaseId
                ) {
                    clase {
                        id
                        name
                        subject { id }
                        docenteBase { id }
                    }
                }
            }
        """
        variables = {
            "name": clase_name_raw,
            "subjectId": str(subject_id),
            "cicloLectivo": ciclo_lectivo,
            "docenteBaseId": docente_base_id,
        }

        try:
            result = execute_graphql_query(mutation, variables)
            if 'errors' in result:
                error_message = str(result['errors'])
                if 'duplicate key value violates unique constraint' in error_message:
                    try:
                        existing_clase = Clase.objects.get(
                            name=clase_name_raw,
                            subject_id=subject_id,
                            ciclo_lectivo=ciclo_lectivo,
                            docente_base_id=docente_base_id
                        )
                        clase_pk_to_new_id[clase_mapping_key] = existing_clase.id
                        print(f'Class already exists (via Django ORM): {{clase_name_raw}} (ID: {{existing_clase.id}})')
                    except Clase.DoesNotExist:
                        print(f'Error creating clase "{clase_name_raw}": {result["errors"]} (and could not find existing via Django ORM)')
                else:
                    print(f'Error creating clase "{{clase_name_raw}}": {{result["errors"]}}')
            else:
                created_count += 1
                clase_id = result['data']['createClase']['clase']['id']
                clase_pk_to_new_id[clase_mapping_key] = clase_id 
                print(f'Created Clase (via GraphQL): {{clase_name_raw}} with ID: {{clase_id}}')
        except Exception as e:
            print(f'Error processing clase "{{clase_name_raw}}": {{e}}')
    
    db_mappings["clase_pk_to_new_id"] = clase_pk_to_new_id
    print(f'Finished importing clases. Created: {{created_count}}')


def import_enrollments_graphql(json_paths, db_mappings):
    print("\n--- Importing Enrollments ---")
    created_count = 0
    updated_count = 0
    error_count = 0

    student_pk_to_new_id = db_mappings.get("student_pk_to_new_id", {{}})
    teacher_pk_to_new_id = db_mappings.get("teacher_pk_to_new_id", {{}})
    clase_pk_to_new_id = db_mappings.get("clase_pk_to_new_id", {{}})

    for json_path in json_paths:
        if not os.path.exists(json_path):
            print(f'JSON file not found at {json_path}')
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {json_path}")
                continue

        if not isinstance(data, list):
            print(f'Expected a list of objects in {json_path}, skipping.')
            continue

        print(f'Processing enrollment mutations from {json_path}...')
        for entry in data:
            mutation_type = entry.get("mutation_type")
            variables = entry.get("variables")

            if mutation_type == "EnrollStudentInClass" and variables:
                old_student_usuario_id = variables.get("studentUsuarioId") or variables.get("student_usuario_id")
                old_clase_id = variables.get("claseId") or variables.get("clase_id")
                old_docente_usuario_id = variables.get("docenteUsuarioId") or variables.get("docente_usuario_id")

                # Lookup new IDs using the stored mappings
                new_student_usuario_id = student_pk_to_new_id.get(str(old_student_usuario_id))
                new_clase_id = clase_pk_to_new_id.get(str(old_clase_id))
                new_docente_usuario_id = teacher_pk_to_new_id.get(str(old_docente_usuario_id)) if old_docente_usuario_id else None

                if not new_student_usuario_id:
                    print(f"--- ERROR (Lookup) ---")
                    print(f"Mutation: EnrollStudentInClass")
                    print(f"Old Student Usuario ID: {{old_student_usuario_id}} not found in student_pk_to_new_id mappings.")
                    print(f"Variables: {{variables}}")
                    print(f"---------------------")
                    error_count += 1
                    continue
                if not new_clase_id:
                    print(f"--- ERROR (Lookup) ---")
                    print(f"Mutation: EnrollStudentInClass")
                    print(f"Old Clase ID: {{old_clase_id}} not found in clase_pk_to_new_id mappings.")
                    print(f"Variables: {{variables}}")
                    print(f"---------------------")
                    error_count += 1
                    continue
                if old_docente_usuario_id and not new_docente_usuario_id:
                    print(f"--- ERROR (Lookup) ---")
                    print(f"Mutation: EnrollStudentInClass")
                    print(f"Old Docente Usuario ID: {{old_docente_usuario_id}} not found in teacher_pk_to_new_id mappings.")
                    print(f"Variables: {{variables}}")
                    print(f"---------------------")
                    error_count += 1
                    continue

                graphql_variables = {
                    "studentUsuarioId": new_student_usuario_id,
                    "claseId": new_clase_id,
                    "docenteUsuarioId": new_docente_usuario_id
                }
                mutation = """
                    mutation EnrollStudentInClass(
                        $studentUsuarioId: ID!,
                        $claseId: ID!,
                        $docenteUsuarioId: ID
                    ) {
                        enrollStudentInClass(
                            studentUsuarioId: $studentUsuarioId,
                            claseId: $claseId,
                            docenteUsuarioId: $docenteUsuarioId
                        ) {
                            enrollment {
                                id
                            }
                        }
                    }
                """
                try:
                    result = execute_graphql_query(mutation, graphql_variables)
                    if 'errors' in result:
                        error_count += 1
                        print(f"--- ERROR ---")
                        print(f"Mutation: EnrollStudentInClass")
                        print(f"Variables: {{graphql_variables}}")
                        print(f"Response: {{result['errors']}}")
                        print(f"-------------")
                    else:
                        created_count += 1
                        print(f'Successfully enrolled student {{graphql_variables.get("studentUsuarioId")}} in class {{graphql_variables.get("claseId")}}')
                except Exception as e:
                    error_count += 1
                    print(f'--- EXCEPTION ---')
                    print(f"Mutation: EnrollStudentInClass")
                    print(f"Variables: {{graphql_variables}}")
                    print(f"Exception: {{e}}")
                    print(f"-----------------")

            elif mutation_type == "AssignDocenteBaseToClase" and variables:
                old_clase_id = variables.get("claseId") or variables.get("clase_id")
                old_docente_id = variables.get("docenteId") or variables.get("docente_id")

                new_clase_id = clase_pk_to_new_id.get(str(old_clase_id))
                new_docente_id = teacher_pk_to_new_id.get(str(old_docente_id))

                if not new_clase_id:
                    print(f"--- ERROR (Lookup) ---")
                    print(f"Mutation: AssignDocenteBaseToClase")
                    print(f"Old Clase ID: {{old_clase_id}} not found in clase_pk_to_new_id mappings.")
                    print(f"Variables: {{variables}}")
                    print(f"---------------------")
                    error_count += 1
                    continue
                if not new_docente_id:
                    print(f"--- ERROR (Lookup) ---")
                    print(f"Mutation: AssignDocenteBaseToClase")
                    print(f"Old Docente ID: {{old_docente_id}} not found in teacher_pk_to_new_id mappings.")
                    print(f"Variables: {{variables}}")
                    print(f"---------------------")
                    error_count += 1
                    continue

                graphql_variables = {
                    "claseId": new_clase_id,
                    "docenteId": new_docente_id
                }
                mutation = """
                    mutation AssignDocenteBaseToClase(
                        $claseId: ID!,
                        $docenteId: ID!
                    ) {
                        assignDocenteBaseToClase(
                            claseId: $claseId,
                            docenteId: $docenteId
                        ) {
                            clase {
                                id
                            }
                        }
                    }
                """
                try:
                    result = execute_graphql_query(mutation, graphql_variables)
                    if 'errors' in result:
                        error_count += 1
                        print(f"--- ERROR ---")
                        print(f"Mutation: AssignDocenteBaseToClase")
                        print(f"Variables: {{graphql_variables}}")
                        print(f"Response: {{result['errors']}}")
                        print(f"-------------")
                    else:
                        updated_count += 1
                        print(f'Successfully assigned docente {{graphql_variables.get("docenteId")}} to clase {{graphql_variables.get("claseId")}}')
                except Exception as e:
                    error_count += 1
                    print(f'--- EXCEPTION ---')
                    print(f"Mutation: AssignDocenteBaseToClase")
                    print(f"Variables: {{graphql_variables}}")
                    print(f"Exception: {{e}}")
                    print(f"-----------------")
            else:
                print(f'Unknown mutation type or missing variables: {{entry}}')
    
    print(f'\nFinished processing enrollments.')
    print(f'  Created/Updated: {{created_count}}')
    print(f'  Docentes Assigned: {{updated_count}}')
    print(f'  Errors: {{error_count}}')


def main():
    db_mappings = load_db_mappings()

    print("\n--- Importing Subjects ---")
    subject_simple_id_map = import_subjects_graphql(json_path='base_de_datos_json/asignaciones_grupales/ASIGNACIONES_agrupaciones.json', db_mappings=db_mappings)
    save_db_mappings(db_mappings) # Save after each major section

    print("\n--- Importing Grade Levels ---")
    import_gradelevels_graphql(path_pattern='base_de_datos_json/estudiantes_matriculados/*.json')
    # Grade levels don't need a mapping for enrollments, so no specific db_mappings update here for now.
    save_db_mappings(db_mappings)

    print("\n--- Importing Teachers ---")
    import_teachers_graphql(json_path='base_de_datos_json/personal_docente/DOCENTES.json', db_mappings=db_mappings)
    save_db_mappings(db_mappings)

    print("\n--- Importing Students ---")
    import_students_graphql(path_pattern='base_de_datos_json/estudiantes_matriculados/*.json', db_mappings=db_mappings)
    save_db_mappings(db_mappings)

    print("\n--- Importing Clases ---")
    import_clases_graphql(json_path='base_de_datos_json/horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json', db_mappings=db_mappings)
    save_db_mappings(db_mappings)

    print("\n--- Importing Enrollments ---")
    enrollment_json_files = [
        os.path.join(os.path.dirname(__file__), 'all_graphql_mutations.json'),
        os.path.join(os.path.dirname(__file__), 'student_enrollment_mutations.json')
    ]
    import_enrollments_graphql(json_paths=enrollment_json_files, db_mappings=db_mappings)
    save_db_mappings(db_mappings)

if __name__ == "__main__":
    main()