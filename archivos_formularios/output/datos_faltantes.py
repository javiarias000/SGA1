import os
import django
import sys
import json
import requests

# Configurar el entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_registry.settings")  
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
django.setup()

# Importar el modelo Usuario
from users.models import Usuario
from utils.etl_normalization import map_grade_level

GRAPHQL_ENDPOINT = "http://web:8000/graphql/"

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

# Mapeo entre nombres de los campos en la base de datos y el JSON 
json_field_mapping = {
    "nombre": ["Apellidos estudiante", "Nombre estudiante"], # Corrected to match observed JSON keys
    "email": "Dirección de correo electrónico",
    "phone": "Número telefónico celular 1",
    "cedula": "Número de Cédula del Estudiante",
    "grade_level_id": ["CURSO", "PARALELO"], 
    "parent_name": ["Apellidos_Representante", "Nombres del Representante del Estudiante"], # Corrected to match observed JSON keys
    "parent_phone": "Número de cédula del Representante",
}

# Ruta al directorio que contiene los archivos JSON de estudiantes
json_directory = "/usr/src/app/base_de_datos_json/estudiantes_matriculados"
json_files = [f for f in os.listdir(json_directory) if f.endswith('.json')]

# GraphQL Mutations
UPDATE_STUDENT_MUTATION = """
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

# Assuming we need to get GradeLevel ID for the mutation
GET_GRADE_LEVEL_ID_QUERY = """
    query GradeLevelByLevelSection($level: String!, $section: String!) {
        allGradeLevels(level: $level, section: $section) {
            id
        }
    }
"""

def get_grade_level_id(level, section):
    variables = {"level": level, "section": section}
    try:
        result = execute_graphql_query(GET_GRADE_LEVEL_ID_QUERY, variables)
        if 'data' in result and result['data']['allGradeLevels']:
            return result['data']['allGradeLevels'][0]['id']
    except Exception as e:
        print(f"Error querying GradeLevel for level {level}, section {section}: {e}")
    return None

print("Actualizando datos de usuarios (estudiantes) via GraphQL basado en archivos JSON:")

updated_count = 0
skipped_count = 0

# Iterar el archivo JSON
for json_file in json_files:
    json_path = os.path.join(json_directory, json_file)
    print(f"Procesando archivo: {json_file}")

    try:
        with open (json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error leyendo {json_file}: {e}")
        continue

    if not isinstance(data, list):
        print(f"Advertencia: Se esperaba una lista de objetos en {json_file}, saltando.")
        continue

    for record in data:
        fields = record.get("fields", {})

        # Extract data using the mapping
        nombre_parts = []
        for part in json_field_mapping["nombre"]:
            if fields.get(part):
                nombre_parts.append(str(fields.get(part)).strip())
        nombre = " ".join(nombre_parts) if nombre_parts else None

        email = fields.get(json_field_mapping["email"])
        phone = fields.get(json_field_mapping["phone"])
        cedula = fields.get(json_field_mapping["cedula"])
        
        curso_raw = fields.get(json_field_mapping["grade_level_id"][0]) if isinstance(json_field_mapping["grade_level_id"], list) else None
        paralelo_raw = fields.get(json_field_mapping["grade_level_id"][1]) if isinstance(json_field_mapping["grade_level_id"], list) else None
        
        grade_level_id = None
        if curso_raw and paralelo_raw:
            parsed_grade_level = map_grade_level(curso_raw, paralelo_raw)
            if parsed_grade_level.level and parsed_grade_level.section:
                grade_level_id = get_grade_level_id(parsed_grade_level.level, parsed_grade_level.section)

        parent_name_parts = []
        if isinstance(json_field_mapping["parent_name"], list):
            for part in json_field_mapping["parent_name"]:
                if fields.get(part):
                    parent_name_parts.append(str(fields.get(part)).strip())
        parent_name = " ".join(parent_name_parts) if parent_name_parts else None
        
        parent_phone = fields.get(json_field_mapping["parent_phone"])

        if not nombre and not cedula and not email:
            print(f"Advertencia: Registro sin 'nombre', 'cedula' o 'email' en {json_file}. Saltando: {record}")
            skipped_count += 1
            continue

        # Prepare GraphQL variables
        graphql_variables = {
            "nombre": nombre,
            "email": email,
            "phone": str(phone) if phone is not None else None,
            "cedula": str(cedula) if cedula is not None else None,
            "gradeLevelId": str(grade_level_id) if grade_level_id is not None else None,
            "parentName": parent_name,
            "parentPhone": str(parent_phone) if parent_phone is not None else None,
        }

        try:
            result = execute_graphql_query(UPDATE_STUDENT_MUTATION, graphql_variables)
            if 'errors' in result:
                print(f"Error actualizando/creando estudiante ({nombre}, {cedula}): {result['errors']}")
                skipped_count += 1
            else:
                updated_count += 1
                print(f"Estudiante actualizado/creado con éxito: {result['data']['createOrUpdateUsuarioStudent']['usuario']['nombre']} (ID: {result['data']['createOrUpdateUsuarioStudent']['usuario']['id']})")
        except Exception as e:
            print(f"Excepción al procesar estudiante ({nombre}, {cedula}): {e}")
            skipped_count += 1

print(f"Proceso completado. Registros actualizados/creados: {updated_count}, Registros saltados: {skipped_count}")