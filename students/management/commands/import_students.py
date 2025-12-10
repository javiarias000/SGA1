import os
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from students.models import Student
from teachers.models import Teacher
from django.db.models.signals import post_save
from teachers.models import create_teacher_profile

class Command(BaseCommand):
    help = 'Import students from JSON files'

    def handle(self, *args, **kwargs):
        # Disconnect the signal
        post_save.disconnect(create_teacher_profile, sender=User)
        self.stdout.write(self.style.NOTICE('Señal create_teacher_profile desconectada temporalmente.'))

        self.stdout.write(self.style.SUCCESS('--- Importando Estudiantes ---'))
        
        json_dir = '/usr/src/base_de_datos_json/estudiantes_matriculados/'
        
        if not os.path.exists(json_dir):
            self.stdout.write(self.style.ERROR(f'Directorio no encontrado: {json_dir}'))
            post_save.connect(create_teacher_profile, sender=User)
            return

        created_count = 0
        updated_count = 0

        for filename in os.listdir(json_dir):
            if not filename.endswith('.json') or 'Total' in filename:
                continue

            file_path = os.path.join(json_dir, filename)
            self.stdout.write(self.style.NOTICE(f'Procesando archivo: {filename}'))

            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f'Error al decodificar JSON en el archivo: {filename}'))
                    continue

            for item in data:
                fields = item.get('fields', {})
                
                email = fields.get('email')
                if not email:
                    self.stdout.write(self.style.WARNING(f"Registro omitido por falta de email: {fields.get('Apellidos')}"))
                    continue

                student_last_name = fields.get('Apellidos', '').strip()
                student_first_name = fields.get('Nombres', '').strip()
                student_full_name = f"{student_first_name} {student_last_name}"
                
                # Create a username from email
                username = email.split('@')[0]

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': student_first_name,
                        'last_name': student_last_name,
                    }
                )

                if user_created:
                    user.set_password('password123')
                    user.save()

                # Find the teacher
                teacher_name = fields.get('Maestro de Instrumento')
                teacher = None
                if teacher_name:
                    try:
                        teacher = Teacher.objects.get(full_name__iexact=teacher_name.strip())
                    except Teacher.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Docente no encontrado: '{teacher_name}' para el estudiante '{student_full_name}'"))
                
                # Parent details
                parent_last_name = fields.get('Apellidos_Representante', '').strip()
                parent_first_name = fields.get('Nombres_Representante', '').strip()
                parent_full_name = f"{parent_first_name} {parent_last_name}"

                student, student_created = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': student_full_name,
                        'grade': fields.get('Año de estudio', ''),
                        'teacher': teacher,
                        'parent_name': parent_full_name,
                        'parent_phone': fields.get('Número telefónico celular 1'),
                        # 'parent_email': fields.get('parent_email'), # Not available
                    }
                )

                if student_created:
                    created_count += 1
                else:
                    # Update existing student
                    student.name = student_full_name
                    student.grade = fields.get('Año de estudio', '')
                    student.teacher = teacher
                    student.parent_name = parent_full_name
                    student.parent_phone = fields.get('Número telefónico celular 1')
                    student.save()
                    updated_count += 1
        
        # Reconnect the signal
        post_save.connect(create_teacher_profile, sender=User)
        self.stdout.write(self.style.NOTICE('Señal create_teacher_profile reconectada.'))
        
        self.stdout.write(self.style.SUCCESS('--- Fin de la importación de estudiantes ---'))
        self.stdout.write(self.style.SUCCESS(f'Nuevos estudiantes creados: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Estudiantes actualizados: {updated_count}'))
