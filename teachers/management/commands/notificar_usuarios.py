import csv
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from teachers.models import Teacher
from students.models import Student

class Command(BaseCommand):
    help = 'Notifica a los usuarios (docentes y estudiantes) su nombre de usuario o genera un reporte.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='El rol a notificar: "teachers", "students", o "all".',
            default='all'
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Envía un correo electrónico de notificación a cada usuario.'
        )
        parser.add_argument(
            '--output-csv',
            type=str,
            help='Ruta del archivo CSV para guardar el reporte. Ej: /tmp/reporte_usuarios.csv'
        )

    def handle(self, *args, **options):
        role = options['role']
        send_email_flag = options['send_email']
        csv_path = options['output_csv']

        if not send_email_flag and not csv_path:
            self.stdout.write(self.style.ERROR('Debes especificar una acción: --send-email o --output-csv <ruta_archivo>'))
            return

        users_to_notify = []
        if role in ['teachers', 'all']:
            self.stdout.write("Obteniendo datos de docentes...")
            # Usamos select_related para optimizar la consulta y evitar un hit a la BD por cada usuario
            for teacher in Teacher.objects.all().select_related('user'):
                if hasattr(teacher, 'user') and teacher.user is not None:
                    users_to_notify.append({
                        'full_name': teacher.user.get_full_name(),
                        'username': teacher.user.username,
                        'email': teacher.user.email,
                        'role': 'Docente'
                    })
        
        if role in ['students', 'all']:
            self.stdout.write("Obteniendo datos de estudiantes...")
            for student in Student.objects.all().select_related('user'):
                 if hasattr(student, 'user') and student.user is not None:
                    users_to_notify.append({
                        'full_name': student.user.get_full_name(),
                        'username': student.user.username,
                        'email': student.user.email,
                        'role': 'Estudiante'
                    })

        if not users_to_notify:
            self.stdout.write(self.style.WARNING('No se encontraron usuarios para notificar.'))
            return
            
        if csv_path:
            self.generate_csv_report(users_to_notify, csv_path)

        if send_email_flag:
            self.send_notifications(users_to_notify)

        self.stdout.write(self.style.SUCCESS('¡Proceso completado!'))

    def generate_csv_report(self, users, path):
        self.stdout.write(f"Generando reporte CSV en: {path}")
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['full_name', 'username', 'email', 'role']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for user_data in users:
                writer.writerow(user_data)
        self.stdout.write(self.style.SUCCESS(f'Reporte guardado exitosamente en {path}'))

    def send_notifications(self, users):
        self.stdout.write("Enviando correos electrónicos...")
        for user_data in users:
            if not user_data['email']:
                self.stdout.write(self.style.WARNING(f"Usuario {user_data['username']} no tiene email. Omitiendo."))
                continue

            subject = 'Bienvenido/a al Sistema de Gestión Académica'
            message = f"""
Hola {user_data['full_name']},

Te damos la bienvenida al Sistema de Gestión Académica del Conservatorio.

Tus credenciales de acceso son:
- Usuario: {user_data['username']}
- Contraseña: [Tu Contraseña Inicial Asignada]

Por favor, guarda esta información en un lugar seguro.

Saludos,
Administración
            """
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_data['email']],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Correo enviado a {user_data['email']}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al enviar correo a {user_data['email']}: {e}"))
