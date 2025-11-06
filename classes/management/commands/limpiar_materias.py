from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

from classes.models import Activity, Clase, Grade, CalificacionParcial, PromedioCache
from teachers.models import Teacher


class Command(BaseCommand):
    help = (
        "Limpia subjects que coinciden con nombres de docentes en Activity/Clase/Grade/CalificacionParcial/PromedioCache.\n"
        "Por defecto hace dry-run. Use --apply para aplicar cambios. Puede definir sujeto por defecto con --default-subject."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica los cambios (por defecto solo muestra el plan).",
        )
        parser.add_argument(
            "--default-subject",
            default="Materia",
            help="Valor de subject a asignar cuando se repara (por defecto: 'Materia').",
        )
        parser.add_argument(
            "--map",
            action="append",
            default=[],
            help=(
                "Mapeos específicos OLD=NEW para reemplazos controlados. "
                "Puede repetirse múltiples veces."
            ),
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        default_subject = options["default_subject"].strip()
        raw_maps = options["map"] or []

        explicit_map = {}
        for item in raw_maps:
            if "=" in item:
                old, new = item.split("=", 1)
                explicit_map[old.strip().lower()] = new.strip()

        teacher_names = set(
            t.full_name.strip().lower()
            for t in Teacher.objects.all()
            if getattr(t, "full_name", None)
        )
        teacher_names |= set(
            ((u.get_full_name() or u.username or "").strip().lower())
            for u in User.objects.filter(teacher_profile__isnull=False)
        )
        teacher_names = {n for n in teacher_names if n}

        if not teacher_names:
            self.stdout.write(self.style.WARNING("No se encontraron nombres de docentes para filtrar."))

        models_and_fields = [
            (Activity, "subject"),
            (Clase, "subject"),
            (Grade, "subject"),
            (CalificacionParcial, "subject"),
            (PromedioCache, "subject"),
        ]

        total_candidates = 0
        total_fixed = 0

        with transaction.atomic():
            for model, field in models_and_fields:
                qs = model.objects.all()
                # Solo donde subject no sea vacío
                qs = qs.exclude(**{f"{field}__isnull": True}).exclude(**{f"{field}": ""})

                # Candidatos: subject que coincide con nombre de docente (case-insensitive)
                candidates = [
                    obj for obj in qs
                    if getattr(obj, field, "").strip().lower() in teacher_names
                ]
                total_candidates += len(candidates)

                for obj in candidates:
                    current = getattr(obj, field).strip()
                    mapped = explicit_map.get(current.lower())
                    new_subject = mapped or default_subject

                    self.stdout.write(
                        f"{model.__name__}#{obj.pk}: '{current}' -> '{new_subject}'"
                    )

                    if apply_changes:
                        setattr(obj, field, new_subject)
                        obj.save(update_fields=[field])
                        total_fixed += 1

            if not apply_changes:
                self.stdout.write(self.style.WARNING("Dry-run: no se aplicaron cambios. Use --apply para confirmar."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Cambios aplicados: {total_fixed}"))

        self.stdout.write(self.style.NOTICE(f"Candidatos detectados: {total_candidates}"))


