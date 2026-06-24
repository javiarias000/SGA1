import pytest
from subjects.models import Subject
from subjects.factories import SubjectFactory


@pytest.mark.django_db
class TestSubjectModel:
    """Tests para el modelo Subject."""

    def test_subject_create(self):
        """Test crear Subject con valores básicos."""
        subject = SubjectFactory(
            name="Violin",
            tipo_materia=Subject.TIPO_MATERIA_CHOICES[2][0]  # INSTRUMENTO
        )
        assert subject.pk is not None
        assert subject.name == "Violin"
        assert subject.tipo_materia == "INSTRUMENTO"

    def test_subject_str(self):
        """Test representación string de Subject."""
        subject = SubjectFactory(name="Piano")
        assert str(subject) == "Piano"

    def test_subject_name_unique(self):
        """Test que name es único."""
        name = "Unique Subject"
        SubjectFactory(name=name)
        with pytest.raises(Exception):  # IntegrityError
            SubjectFactory(name=name)

    def test_subject_default_tipo_materia(self):
        """Test tipo_materia por defecto."""
        subject = SubjectFactory()
        assert subject.tipo_materia in [choice[0] for choice in Subject.TIPO_MATERIA_CHOICES]

    def test_subject_description(self):
        """Test campo description."""
        description = "Clase de teoría musical avanzada"
        subject = SubjectFactory(description=description)
        assert subject.description == description

    def test_subject_all_tipo_materia_choices(self):
        """Test todos los tipos de materia."""
        tipos = [choice[0] for choice in Subject.TIPO_MATERIA_CHOICES]
        assert "TEORIA" in tipos
        assert "AGRUPACION" in tipos
        assert "INSTRUMENTO" in tipos
        assert "OTRO" in tipos
