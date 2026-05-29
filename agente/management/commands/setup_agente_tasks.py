from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Registra las tareas periódicas del Agente IA en Celery Beat'

    def handle(self, *args, **options):
        from django_celery_beat.models import PeriodicTask, CrontabSchedule

        # Lunes a las 07:00 — análisis semanal completo
        lunes_7am, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='7', day_of_week='1',
            day_of_month='*', month_of_year='*',
        )
        PeriodicTask.objects.update_or_create(
            name='Agente IA — Análisis semanal de rendimiento',
            defaults={
                'crontab': lunes_7am,
                'task': 'agente.tasks.analizar_rendimiento_semanal',
                'enabled': True,
            },
        )

        # Diariamente a las 08:00 — envío de notificaciones pendientes
        diario_8am, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='8', day_of_week='*',
            day_of_month='*', month_of_year='*',
        )
        PeriodicTask.objects.update_or_create(
            name='Agente IA — Envío de notificaciones pendientes',
            defaults={
                'crontab': diario_8am,
                'task': 'agente.tasks.enviar_notificaciones_pendientes',
                'enabled': True,
            },
        )

        self.stdout.write(self.style.SUCCESS('✅ Tareas periódicas del Agente IA registradas correctamente.'))
