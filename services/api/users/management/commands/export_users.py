from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import json

class Command(BaseCommand):
    help = 'Exports all users to the console'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Exporting Users ---'))
        
        users = User.objects.all()
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found in the database.'))
            return

        for user in users:
            user_data = {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
            self.stdout.write(json.dumps(user_data, indent=2))

        self.stdout.write(self.style.SUCCESS(f'--- Exported {users.count()} users ---'))
