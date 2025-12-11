from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class CustomBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        # 1. First, try to authenticate with the default ModelBackend logic
        # This will check for username match
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user:
            return user

        # 2. If default authentication fails, try to find a user by email
        try:
            user = UserModel.objects.get(email=username)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            pass

        # 3. If still not found, try to treat the username as a short version of an email
        if '@' not in username:
            try:
                # Assuming the domain is always 'docentes.educacion.edu.ec' for teachers
                email_to_try = f"{username}@docentes.educacion.edu.ec"
                user = UserModel.objects.get(email=email_to_try)
                if user.check_password(password):
                    return user
            except UserModel.DoesNotExist:
                pass
        
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None