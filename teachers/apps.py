from django.apps import AppConfig


class TeachersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teachers'
    verbose_name = 'Gestión de Docentes'
    
    def ready(self):
        import teachers.models  