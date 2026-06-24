import json
import os

# --- Rutas de los archivos ---
# Ajusta estas rutas si la estructura de tu proyecto cambia.
RUTA_BASE_JSON = '../base_de_datos_json'
RUTA_DOCENTES = os.path.join(RUTA_BASE_JSON, 'personal_docente', 'DOCENTES.json')
RUTA_AGRUPACIONES = os.path.join(RUTA_BASE_JSON, 'asignaciones_grupales', 'ASIGNACIONES_agrupaciones.json')
RUTA_ASIGNACIONES_MANUALES = os.path.join(RUTA_BASE_JSON, 'manual_teacher_assignments.json')

def cargar_datos(ruta_archivo):
    """
    Carga datos desde un archivo JSON. Si el archivo no existe,
    devuelve una lista vacía.
    """
    if not os.path.exists(ruta_archivo):
        print(f"Advertencia: El archivo {ruta_archivo} no fue encontrado. Se creará uno nuevo si es necesario.")
        return []
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error al leer el archivo {ruta_archivo}: {e}")
        return []

def guardar_datos(ruta_archivo, datos):
    """Guarda una lista de diccionarios en un archivo JSON con formato legible."""
    try:
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Asignaciones guardadas correctamente en {ruta_archivo}")
    except IOError as e:
        print(f"Error al guardar el archivo {ruta_archivo}: {e}")

def mostrar_lista_numerada(titulo, lista, campo_a_mostrar):
    """Muestra una lista de elementos de forma numerada y legible."""
    print(f"\n--- {titulo} ---")
    if not lista:
        print("No hay elementos para mostrar.")
        return
    
    for i, item in enumerate(lista):
        # Para docentes, unir nombre y apellido si existen
        if isinstance(item, dict) and 'NOMBRES' in item and 'APELLIDOS' in item:
            texto = f"{item.get('NOMBRES', '')} {item.get('APELLIDOS', '')}".strip()
            print(f"{i + 1}. {texto}")
        # Para otros diccionarios, usar el campo especificado
        elif isinstance(item, dict) and campo_a_mostrar in item:
            print(f"{i + 1}. {item[campo_a_mostrar]}")
        else:
            print(f"{i + 1}. {item}")


def obtener_seleccion_usuario(lista):
    """Solicita al usuario que elija un elemento de la lista y lo devuelve."""
    while True:
        try:
            opcion = input(f"Seleccione un número (1-{len(lista)}) o 0 para cancelar: ")
            opcion_int = int(opcion)
            if 0 <= opcion_int <= len(lista):
                return opcion_int
            else:
                print("❌ Opción fuera de rango. Por favor, intente de nuevo.")
        except ValueError:
            print("❌ Entrada no válida. Por favor, ingrese solo un número.")

def main():
    """Función principal del script de asignación."""
    print("--- Asistente para Asignación Manual de Docentes a Agrupaciones ---")

    # Cargar todos los datos necesarios
    docentes = cargar_datos(RUTA_DOCENTES)
    agrupaciones_todas = cargar_datos(RUTA_AGRUPACIONES)
    asignaciones_manuales = cargar_datos(RUTA_ASIGNACIONES_MANUALES)

    if not docentes or not agrupaciones_todas:
        print("\nNo se pudieron cargar los datos de docentes o agrupaciones. Finalizando script.")
        return

    while True:
        # Filtrar agrupaciones que ya tienen una asignación manual
        agrupaciones_asignadas = {asignacion['agrupacion'] for asignacion in asignaciones_manuales}
        agrupaciones_sin_asignar = [
            agrup for agrup in agrupaciones_todas 
            if agrup.get('nombre_agrupacion') not in agrupaciones_asignadas
        ]

        if not agrupaciones_sin_asignar:
            print("\n¡Felicidades! Todas las agrupaciones ya tienen un docente asignado.")
            break

        # 1. Seleccionar Agrupación
        mostrar_lista_numerada("Agrupaciones sin Docente Asignado", agrupaciones_sin_asignar, 'nombre_agrupacion')
        indice_agrupacion = obtener_seleccion_usuario(agrupaciones_sin_asignar)
        
        if indice_agrupacion == 0:
            break
        
        agrupacion_seleccionada = agrupaciones_sin_asignar[indice_agrupacion - 1]
        nombre_agrupacion = agrupacion_seleccionada['nombre_agrupacion']

        # 2. Seleccionar Docente
        mostrar_lista_numerada("Lista de Docentes Disponibles", docentes, 'NOMBRES')
        indice_docente = obtener_seleccion_usuario(docentes)
        
        if indice_docente == 0:
            print("Asignación cancelada.")
            continue # Volver al menú de agrupaciones
            
        docente_seleccionado = docentes[indice_docente - 1]
        nombre_docente = f"{docente_seleccionado.get('NOMBRES', '')} {docente_seleccionado.get('APELLIDOS', '')}".strip()
        
        # 3. Confirmar y guardar la asignación
        print(f"\nConfirme la asignación:")
        print(f"  - Agrupación: {nombre_agrupacion}")
        print(f"  - Docente:    {nombre_docente}")
        
        confirmacion = input("¿Es correcta esta asignación? (s/n): ").lower()
        
        if confirmacion == 's':
            nueva_asignacion = {
                "agrupacion": nombre_agrupacion,
                "docente": nombre_docente,
                "id_docente": docente_seleccionado.get("ID_DOCENTE", None)
            }
            asignaciones_manuales.append(nueva_asignacion)
            guardar_datos(RUTA_ASIGNACIONES_MANUALES, asignaciones_manuales)
        else:
            print("Asignación descartada.")

        # 4. Continuar o salir
        continuar = input("\n¿Desea asignar otro docente? (s/n): ").lower()
        if continuar != 's':
            break

    print("\n--- Proceso de asignación finalizado. ---")

if __name__ == "__main__":
    main()
