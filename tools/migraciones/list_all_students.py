
import os
import django

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_registry.settings')
django.setup()

from students.models import Student

def list_all_students_in_db():
    """
    Lista todos los estudiantes activos en la base de datos con sus IDs y nombres.
    """
    print("--- LISTANDO ESTUDIANTES ACTIVOS ---")

    students = Student.objects.filter(active=True).select_related('usuario').order_by('usuario__nombre')

    if not students.exists():
        print("\nNo se encontraron estudiantes activos en la base de datos.")
        return

    print(f"\nSe encontraron {students.count()} estudiantes activos:")
    print("="*40)
    print(f"{ 'ID':<10} | {'Nombre del Estudiante'}")
    print(f"{'-'*10} | {'-'*28}")

    for student in students:
        student_name = student.usuario.nombre if student.usuario else "Usuario no asociado"
        print(f"{student.id:<10} | {student_name}")
    
    print("="*40)
    print("\nVerifica si el estudiante con ID 1666 aparece en esta lista.")

if __name__ == '__main__':
    list_all_students_in_db()
