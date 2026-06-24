from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

from subjects.models import Subject
from teachers.models import Teacher


class Command(BaseCommand):
    help = (
        "Limpia y elimina Subjects que coinciden con nombres de docentes."
        "Por defecto hace dry-run. Use --apply para aplicar cambios."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica los cambios (por defecto solo muestra el plan).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

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
            return

        subjects_to_delete = Subject.objects.filter(name__in=teacher_names)
        
        total_candidates = subjects_to_delete.count()

        with transaction.atomic():
            for subject in subjects_to_delete:
                self.stdout.write(
                    f"Subject a eliminar: '{subject.name}'"
                )

                if apply_changes:
                    subject.delete()

            if not apply_changes:
                self.stdout.write(self.style.WARNING("Dry-run: no se aplicaron cambios. Use --apply para confirmar."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Cambios aplicados: {total_candidates} subjects eliminados."))

        self.stdout.write(self.style.NOTICE(f"Candidatos detectados: {total_candidates}"))