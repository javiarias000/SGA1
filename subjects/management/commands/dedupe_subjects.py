import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from classes.models import Activity, CalificacionParcial, Clase, PromedioCache, Enrollment, Deber, Horario
from subjects.models import Subject
from utils.etl_normalization import norm_key


@dataclass
class SubjectRefs:
    clases: int = 0
    activities: int = 0
    grades: int = 0
    calif_parciales: int = 0
    promedio_cache: int = 0


def _tipo_priority(tipo: str) -> int:
    # smaller is preferred
    order = {
        'TEORIA': 0,
        'AGRUPACION': 1,
        'INSTRUMENTO': 2,
        'OTRO': 9,
    }
    return order.get(tipo or 'OTRO', 9)


class Command(BaseCommand):
    help = 'Deduplica materias (subjects.Subject) por key normalizada (acentos/mayúsculas) y reasigna FKs a una materia canónica.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Aplica cambios (sin esto, solo muestra el plan).')
        parser.add_argument('--base-dir', default='base_de_datos_json', help='Para escribir logs de reversión en base_de_datos_json/etl_logs/.')

    def handle(self, *args, **opts):
        apply: bool = opts['apply']
        base_dir: str = opts['base_dir']

        subjects = list(Subject.objects.all())
        groups: Dict[str, List[Subject]] = defaultdict(list)
        for s in subjects:
            groups[norm_key(s.name)].append(s)

        dup_groups = [(k, v) for k, v in groups.items() if len(v) > 1]
        if not dup_groups:
            self.stdout.write(self.style.SUCCESS('No duplicate subjects found.'))
            return

        # Build a plan
        plan = []

        for key, items in sorted(dup_groups, key=lambda kv: kv[0]):
            # pick canonical
            items_sorted = sorted(items, key=lambda s: (_tipo_priority(s.tipo_materia), s.id))
            canonical = items_sorted[0]
            aliases = items_sorted[1:]

            for alias in aliases:
                refs = SubjectRefs(
                    clases=Clase.objects.filter(subject=alias).count(),
                    activities=Activity.objects.filter(subject=alias).count(),
                    grades=CalificacionParcial.objects.filter(subject=alias).count(),
                    calif_parciales=CalificacionParcial.objects.filter(subject=alias).count(),
                    promedio_cache=PromedioCache.objects.filter(subject=alias).count(),
                )
                plan.append({
                    'key': key,
                    'canonical': {'id': canonical.id, 'name': canonical.name, 'tipo_materia': canonical.tipo_materia},
                    'alias': {'id': alias.id, 'name': alias.name, 'tipo_materia': alias.tipo_materia},
                    'refs': refs.__dict__,
                })

        # Print summary
        self.stdout.write(self.style.WARNING(f'Found {len(dup_groups)} duplicate subject groups; {len(plan)} alias subjects would be merged.'))
        for entry in plan[:30]:
            c = entry['canonical']
            a = entry['alias']
            r = entry['refs']
            self.stdout.write(
                f"- merge Subject#{a['id']} '{a['name']}' -> Subject#{c['id']} '{c['name']}' "
                f"(refs: clases={r['clases']}, activities={r['activities']}, grades={r['grades']}, calif_parciales={r['calif_parciales']}, promedio_cache={r['promedio_cache']})"
            )
        if len(plan) > 30:
            self.stdout.write(self.style.WARNING(f'... and {len(plan) - 30} more'))

        if not apply:
            self.stdout.write(self.style.NOTICE('Dry-run only. Re-run with --apply to execute.'))
            return

        # Apply changes transactionally and write rollback log
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        logs_dir = os.path.join(base_dir, 'etl_logs')
        os.makedirs(logs_dir, exist_ok=True)
        rollback_path = os.path.join(logs_dir, f'dedupe_subjects_{ts}.json')

        with transaction.atomic():
            for entry in plan:
                canonical_id = entry['canonical']['id']
                alias_id = entry['alias']['id']
                canonical_subject = Subject.objects.get(id=canonical_id)

                # Handle Clase merge logic
                clases_to_merge = Clase.objects.filter(subject_id=alias_id)
                for clase_to_merge in clases_to_merge:
                    # Check for conflict
                    conflicting_clase = Clase.objects.filter(
                        subject_id=canonical_id,
                        ciclo_lectivo=clase_to_merge.ciclo_lectivo,
                        docente_base=clase_to_merge.docente_base,
                        paralelo=clase_to_merge.paralelo
                    ).first()

                    if conflicting_clase:
                        # Conflict exists: merge enrollments and other related models, then delete
                        self.stdout.write(self.style.WARNING(f"  Merging Clase ID {clase_to_merge.id} into {conflicting_clase.id}"))
                        
                        # Move Enrollments
                        Enrollment.objects.filter(clase=clase_to_merge).update(clase=conflicting_clase)
                        # Move Activities
                        Activity.objects.filter(clase=clase_to_merge).update(clase=conflicting_clase)
                        # Move Deberes
                        Deber.objects.filter(clase=clase_to_merge).update(clase=conflicting_clase)
                        # Move Horarios
                        Horario.objects.filter(clase=clase_to_merge).update(clase=conflicting_clase)

                        # After moving all relations, delete the redundant clase
                        clase_to_merge.delete()
                    else:
                        # No conflict, just update the subject
                        clase_to_merge.subject = canonical_subject
                        clase_to_merge.save()

                # Rewrite FKs for other models (these don't have unique constraints that would cause conflicts like Clase)
                Activity.objects.filter(subject_id=alias_id).update(subject_id=canonical_id)
                CalificacionParcial.objects.filter(subject_id=alias_id).update(subject_id=canonical_id)
                CalificacionParcial.objects.filter(subject_id=alias_id).update(subject_id=canonical_id)
                PromedioCache.objects.filter(subject_id=alias_id).update(subject_id=canonical_id)

                # Finally, delete the alias subject
                Subject.objects.filter(id=alias_id).delete()

            with open(rollback_path, 'w', encoding='utf-8') as f:
                json.dump({'applied_at_utc': ts, 'plan': plan}, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Applied subject dedupe. Rollback log written to {rollback_path}'))