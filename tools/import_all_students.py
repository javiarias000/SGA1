#!/usr/bin/env python3
"""
Import all 427 students from normalizado_4nf into database.
Reads CSV files organized by course (1o/, 2o/, etc.) and creates Usuario + Student records.
"""
import os
import csv
import sys
from pathlib import Path

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_registry.settings')
sys.path.insert(0, '/app')

import django
django.setup()

from users.models import Usuario
from students.models import Student
from classes.models import GradeLevel

BASE_DIR = Path('/home/jav/SGA1/base_de_datos_json/normalizado_4nf')

# Course -> level mapping
COURSE_LEVEL = {
    '1o': '1', '2o': '2', '3o': '3', '4o': '4', '5o': '5',
    '6o': '6', '7o': '7', '8o': '8', '9o': '9', '10o': '10',
    '11o': '11', '1o_Extra': '1'
}

total_created = 0
total_existing = 0
total_errors = 0

for course_dir in sorted(BASE_DIR.iterdir()):
    if not course_dir.is_dir():
        continue

    course_name = course_dir.name
    level = COURSE_LEVEL.get(course_name)
    if not level:
        continue

    csv_file = course_dir / '1_estudiantes.csv'
    if not csv_file.exists():
        print(f"⚠ {course_name}: no CSV found")
        continue

    created_count = 0
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cedula = row.get('id', '').strip()
            apellidos = row.get('apellidos', '').strip()
            nombres = row.get('nombres', '').strip()
            email = row.get('email', '').strip()

            if not cedula or not apellidos:
                continue

            nombre_completo = f"{apellidos} {nombres}".strip() if nombres else apellidos

            # Check if student exists
            try:
                usuario, created = Usuario.objects.get_or_create(
                    cedula=cedula,
                    defaults={
                        'rol': Usuario.Rol.ESTUDIANTE,
                        'nombre': nombre_completo,
                        'email': email if email and '@' in email else None,
                    }
                )

                if created:
                    created_count += 1
                    total_created += 1

                    # Create Student profile
                    try:
                        gl, _ = GradeLevel.objects.get_or_create(level=level, section='')
                        Student.objects.get_or_create(
                            usuario=usuario,
                            defaults={'grade_level': gl, 'active': True}
                        )
                    except Exception as e:
                        print(f"  Error creating Student profile for {nombre_completo}: {e}")
                        total_errors += 1
                else:
                    total_existing += 1

            except Exception as e:
                print(f"  Error with {cedula}: {e}")
                total_errors += 1

    if created_count > 0:
        print(f"✓ {course_name:10} ({level}): {created_count} new")
    else:
        print(f"→ {course_name:10} ({level}): all existing")

print(f"\n{'='*60}")
print(f"Created: {total_created} | Existing: {total_existing} | Errors: {total_errors}")
print(f"Total in DB: {Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE).count()}")
