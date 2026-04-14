import json
import os

json_base_dir = '/Users/javi000/Documents/SGA/base_de_datos_json'
instrumento_dir = os.path.join(json_base_dir, 'Instrumento_Agrupaciones')
agrupaciones_dir = os.path.join(json_base_dir, 'asignaciones_grupales')

unique_subjects_for_manual_assignment = set()

# Process Instrumento_Agrupaciones files
if os.path.exists(instrumento_dir):
    for filename in os.listdir(instrumento_dir):
        if filename.endswith('.json') and \
           filename not in ['ESTUDIANTES_CON_REPRESENTANTES.json', 'ASIGNACIONES_instrumento_que_estudia_en_el_conservatorio_bolívar.json']:
            file_path = os.path.join(instrumento_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    fields = item.get('fields', {})
                    # Standardized name after user's renaming script
                    clase_name = fields.get('clase', '').strip() 
                    if clase_name:
                        unique_subjects_for_manual_assignment.add(clase_name)
            except Exception as e:
                print('Error reading {}: {}'.format(file_path, e))

# Process ASIGNACIONES_agrupaciones.json
agrupaciones_file_path = os.path.join(agrupaciones_dir, 'ASIGNACIONES_agrupaciones.json')
if os.path.exists(agrupaciones_file_path):
    try:
        with open(agrupaciones_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            fields = item.get('fields', {})
            # Standardized name after user's renaming script
            clase_name = fields.get('clase', '').strip() 
            if clase_name:
                unique_subjects_for_manual_assignment.add(clase_name)
    except Exception as e:
        print('Error reading {}: {}'.format(agrupaciones_file_path, e))

manual_assignments = []
for subject_name in sorted(list(unique_subjects_for_manual_assignment)):
    manual_assignments.append({
        "subject_name": subject_name,
        "docente_nombre": "" # Placeholder for manual entry
    })

output_file = os.path.join(json_base_dir, 'manual_teacher_assignments.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(manual_assignments, f, indent=2, ensure_ascii=False)

print('Generated manual assignment template: {}'.format(output_file))
