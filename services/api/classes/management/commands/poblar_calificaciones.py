from django.core.management.base import BaseCommand
from classes.models import TipoAporte

class Command(BaseCommand):
    help = 'Pobla la base de datos con los tipos de aportes predeterminados'

    def handle(self, *args, **kwargs):
        """
        Crea los tipos de aportes basados en tu formato de Excel:
        - Tema / Trabajo en clase
        - Exposición del Deber
        - Transcripción
        - Deber N1, N2, N3
        """
        
        tipos_aportes = [
            {
                'nombre': 'Tema / Trabajo en clase',
                'codigo': 'TEMA_CLASE',
                'descripcion': 'Trabajo realizado durante la clase',
                'peso': 1.0,
                'orden': 1
            },
            {
                'nombre': 'Exposición del Deber',
                'codigo': 'EXPOSICION',
                'descripcion': 'Presentación y exposición de tareas asignadas',
                'peso': 1.0,
                'orden': 2
            },
            {
                'nombre': 'Transcripción',
                'codigo': 'TRANSCRIPCION',
                'descripcion': 'Trabajos de transcripción musical',
                'peso': 1.0,
                'orden': 3
            },
            {
                'nombre': 'Deber N°1',
                'codigo': 'DEBER_1',
                'descripcion': 'Primera tarea del parcial',
                'peso': 1.0,
                'orden': 4
            },
            {
                'nombre': 'Deber N°2',
                'codigo': 'DEBER_2',
                'descripcion': 'Segunda tarea del parcial',
                'peso': 1.0,
                'orden': 5
            },
            {
                'nombre': 'Deber N°3',
                'codigo': 'DEBER_3',
                'descripcion': 'Tercera tarea del parcial',
                'peso': 1.0,
                'orden': 6
            },
            {
                'nombre': 'Evaluación Parcial',
                'codigo': 'EVAL_PARCIAL',
                'descripcion': 'Evaluación del parcial',
                'peso': 1.5,  # Peso mayor para examen
                'orden': 7
            },
            {
                'nombre': 'Proyecto',
                'codigo': 'PROYECTO',
                'descripcion': 'Trabajo de proyecto o investigación',
                'peso': 1.2,
                'orden': 8
            },
        ]
        
        creados = 0
        actualizados = 0
        
        for tipo_data in tipos_aportes:
            tipo, created = TipoAporte.objects.get_or_create(
                codigo=tipo_data['codigo'],
                defaults=tipo_data
            )
            
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Creado: {tipo.nombre}')
                )
            else:
                # Actualizar si ya existe
                for key, value in tipo_data.items():
                    if key != 'codigo':
                        setattr(tipo, key, value)
                tipo.save()
                actualizados += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Actualizado: {tipo.nombre}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado:\n'
                f'   • {creados} tipos de aportes creados\n'
                f'   • {actualizados} tipos de aportes actualizados'
            )
        )