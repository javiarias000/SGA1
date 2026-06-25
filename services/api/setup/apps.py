from django.apps import AppConfig

class SetupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'setup'
    verbose_name = '⚙️ Configuración'

    def ready(self):
        from config.admin_order import install_custom_app_list
        install_custom_app_list()
