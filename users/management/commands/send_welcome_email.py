from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from users.utils import send_welcome_email_with_temporary_password

class Command(BaseCommand):
    help = 'Envía un correo de bienvenida a un usuario con una contraseña temporal.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='El nombre de usuario del destinatario.')

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'El usuario "{username}" no existe.')

        if not user.email:
            raise CommandError(f'El usuario "{username}" no tiene una dirección de correo electrónico configurada.')

        self.stdout.write(f'Enviando correo de bienvenida a {user.username} ({user.email})...')
        
        try:
            send_welcome_email_with_temporary_password(user)
            self.stdout.write(self.style.SUCCESS(f'¡Correo enviado exitosamente a {user.username} a la dirección {user.email}!'))
            self.stdout.write(self.style.WARNING('La contraseña se imprimirá en la consola porque estás en modo de desarrollo.'))
        except Exception as e:
            raise CommandError(f'Ocurrió un error al enviar el correo: {e}')
