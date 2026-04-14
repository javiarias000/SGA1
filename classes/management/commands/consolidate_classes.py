import os
from django.core.management.base import BaseCommand
from django.db.models import Count
from classes.models import Clase, Subject

class Command(BaseCommand):
    help = 'Consolida clases duplicadas y elimina las que están vacías.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando proceso de consolidación de clases..."))

        all_subjects = Subject.objects.all()
        clases_a_eliminar = []

        for subject in all_subjects:
            # Encontrar todas las clases para una misma materia
            clases_por_materia = Clase.objects.filter(subject=subject)

            if clases_por_materia.count() <= 1:
                continue

            self.stdout.write(f"\n--- Procesando materia: '{subject.name}' ({clases_por_materia.count()} clases encontradas) ---")

            # Agrupar por docente_base
            docentes = clases_por_materia.values('docente_base').distinct()

            for d in docentes:
                docente_id = d['docente_base']
                
                # Clases para esta materia y este docente
                clases_grupo = clases_por_materia.filter(docente_base_id=docente_id).annotate(num_enrollments=Count('enrollments'))
                
                if clases_grupo.count() <= 1:
                    continue

                self.stdout.write(f"  - Verificando duplicados para docente ID: {docente_id}...")

                # Encontrar la clase "principal" (la que tiene más inscripciones, o la más antigua si hay empate)
                clase_principal = None
                max_enrollments = -1
                
                for clase in clases_grupo:
                    if clase.num_enrollments > max_enrollments:
                        max_enrollments = clase.num_enrollments
                        clase_principal = clase
                
                # Si encontramos una clase principal (con o sin alumnos), el resto son candidatas a eliminación
                if clase_principal:
                    self.stdout.write(f"    -> Clase principal seleccionada: ID {clase_principal.id} ({clase_principal.num_enrollments} inscripciones)")
                    
                    for clase in clases_grupo:
                        if clase.id != clase_principal.id:
                            if clase.num_enrollments > 0:
                                self.stdout.write(self.style.WARNING(f"      -> ¡ADVERTENCIA! La clase duplicada ID {clase.id} tiene {clase.num_enrollments} inscripciones. No se eliminará, requiere revisión manual."))
                            else:
                                self.stdout.write(f"      -> Marcando para eliminar clase duplicada vacía: ID {clase.id}")
                                clases_a_eliminar.append(clase.id)
                else:
                    self.stdout.write(self.style.NOTICE(f"    -> No se pudo determinar una clase principal para este grupo."))


        if not clases_a_eliminar:
            self.stdout.write(self.style.SUCCESS("\nNo se encontraron clases duplicadas vacías para eliminar."))
        else:
            self.stdout.write(self.style.WARNING(f"\nSe eliminarán {len(clases_a_eliminar)} clases duplicadas vacías..."))
            
            # Eliminar las clases
            Clase.objects.filter(id__in=clases_a_eliminar).delete()
            
            self.stdout.write(self.style.SUCCESS("¡Eliminación completada!"))

        self.stdout.write(self.style.SUCCESS("\n--- Proceso de consolidación finalizado ---"))
