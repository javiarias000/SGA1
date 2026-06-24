from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Sets the password for a given user.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='The username of the user.')
        parser.add_argument('password', type=str, help='The new password for the user.')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        password = kwargs['password']
        try:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully changed password for "{username}"'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with username "{username}" does not exist.'))
