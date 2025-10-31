from django.core.management.base import BaseCommand
from students.models import Student
from utils.notifications import NotificacionEmail

class Command(BaseCommand):
    help = 'Envía un email de reporte de calificaciones para un estudiante dado'

    def add_arguments(self, parser):
        parser.add_argument('student_id', type=int, help='ID del estudiante')
        parser.add_argument('email', type=str, help='Email de destino')

    def handle(self, *args, **options):
        sid = options['student_id']
        email = options['email']
        try:
            estudiante = Student.objects.get(id=sid)
        except Student.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Estudiante {sid} no existe'))
            return
        self.stdout.write(f'Enviando reporte de {estudiante.name} a {email}...')
        ok = NotificacionEmail.enviar_reporte_calificaciones(estudiante, email)
        if ok:
            self.stdout.write(self.style.SUCCESS('✅ Email enviado (console backend en desarrollo)'))
        else:
            self.stderr.write(self.style.ERROR('❌ Falló el envío'))