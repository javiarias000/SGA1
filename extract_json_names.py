import json

json_file_path = 'base_de_datos_json/asignaciones_grupales/ASIGNACIONES_agrupaciones.json'
output_file_path = '/Users/javi000/.gemini/tmp/7ee9fa71869d40ada58c077b7bcaa473e114dee96207822bb48088c40085b528/json_student_names_extracted.txt'

try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        for entry in data:
            if entry.get('numero') != 'No':
                outfile.write(entry.get('nombre_completo', '').strip() + '\n')
    print("Extracted names to " + output_file_path) # Removed f-string
except FileNotFoundError:
    print("Error: JSON file not found at " + json_file_path) # Removed f-string
except json.JSONDecodeError:
    print("Error: Could not decode JSON from " + json_file_path) # Removed f-string