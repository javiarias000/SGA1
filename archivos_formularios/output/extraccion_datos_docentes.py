import os
import django
import sys

# Configurar el entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_registry.settings")  # Reemplaza con tu archivo de configuración
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
django.setup()

# Importar el modelo Usuario
from users.models import Usuario

print("Verificando datos faltantes en el model Usuario:")
usuarios = Usuario.objects.all()

for usuario in usuarios:
    datos_faltantes = False
    campos_faltantes = []

    for field in Usuario._meta.get_fields():
        # Excluir campos relacionales y automáticos
        if field.is_relation:
            continue

        # Obtener el valor del campo
        value = getattr(usuario, field.name, None)

        # Verificar si el valor esta vacio o es nulo 
        if value is None or value == "":
            datos_faltantes = True
            campos_faltantes.append(field.name)
    
    # Imprimir solo si hay datos faltantes
    if datos_faltantes: 
        print(f"Usuario ID: {usuario.id}, Nombre: {usuario.nombre}")
        print(f"  - Campos faltantes: {', '.join(campos_faltantes)}")