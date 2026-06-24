import json
import os

json_base_dir = '/Users/javi000/Documents/SGA/base_de_datos_json'
agrupaciones_dir = os.path.join(json_base_dir, 'asignaciones_grupales')

unique_agrupaciones = set()

# Process ASIGNACIONES_agrupaciones.json
agrupaciones_file_path = os.path.join(agrupaciones_dir, 'ASIGNACIONES_agrupaciones.json')
if os.path.exists(agrupaciones_file_path):
    try:
        with open(agrupaciones_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            fields = item.get('fields', {})
            agrupacion_name = fields.get('agrupacion', '').strip()
            if agrupacion_name:
                unique_agrupaciones.add(agrupacion_name)
    except Exception as e:
        print('Error reading {}: {}'.format(agrupaciones_file_path, e))
else:
    print('Error: ASIGNACIONES_agrupaciones.json not found at {}'.format(agrupaciones_file_path))


manual_assignments = []
for agrupacion_name in sorted(list(unique_agrupaciones)):
    manual_assignments.append({
        "agrupacion_name": agrupacion_name,
        "docente_nombre": "" # Placeholder for manual entry
    })

output_file = os.path.join(json_base_dir, 'manual_teacher_assignments.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(manual_assignments, f, indent=2, ensure_ascii=False)

print('Generated manual assignment template for Agrupaciones: {}'.format(output_file))
