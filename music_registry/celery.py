import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_registry.settings')

app = Celery('music_registry')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configuración de tareas programadas
app.conf.beat_schedule = {
    'reportes-quimestrales': {
        'task': 'classes.tasks.enviar_reportes_quimestrales',
        'schedule': crontab(day_of_month='15', hour=8),  # Día 15 a las 8am
    },
    'verificacion-semanal': {
        'task': 'classes.tasks.verificar_rendimiento_semanal',
        'schedule': crontab(day_of_week='monday', hour=8),  # Lunes 8am
    },
}