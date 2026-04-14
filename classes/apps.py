from django.apps import AppConfig


class ClassesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'classes'
    verbose_name = 'Gestión de Clases y Actividades'

    def ready(self):
        import classes.signals  # noqa: F401 — registra señales