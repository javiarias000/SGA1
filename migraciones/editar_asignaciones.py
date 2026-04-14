
import json
import os

# Ruta al archivo JSON principal, que está un nivel más arriba
RUTA_ASIGNACIONES = '../asignaciones_docentes.json'

def cargar_datos():
    """Carga los datos de asignaciones desde el archivo JSON."""
    if not os.path.exists(RUTA_ASIGNACIONES):
        print(f"Error: El archivo {RUTA_ASIGNACIONES} no fue encontrado.")
        return None
    try:
        with open(RUTA_ASIGNACIONES, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error al leer el archivo {RUTA_ASIGNACIONES}: {e}")
        return None

def guardar_datos(datos):
    """Guarda los datos actualizados en el archivo JSON."""
    try:
        with open(RUTA_ASIGNACIONES, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        print("\n✅ ¡Asignación guardada con éxito!")
    except IOError as e:
        print(f"Error al guardar el archivo {RUTA_ASIGNACIONES}: {e}")

def main():
    """Función principal para editar las asignaciones de docentes."""
    print("--- Editor de Asignaciones de Docentes ---")
    
    while True:
        datos = cargar_datos()
        if datos is None:
            break

        # Prioriza mostrar agrupaciones que aún no tienen docente
        agrupaciones_sin_asignar = [agrup for agrup in datos if not agrup.get('docente_asignado', '').strip()]
        
        if agrupaciones_sin_asignar:
            agrupaciones_a_mostrar = agrupaciones_sin_asignar
            titulo = "Agrupaciones sin Docente"
        else:
            print("\n¡Felicidades! Todas las agrupaciones ya tienen un docente.")
            modificar = input("¿Desea modificar alguna asignación existente? (s/n): ").lower()
            if modificar != 's':
                break
            agrupaciones_a_mostrar = datos # Mostrar todas para modificar
            titulo = "Todas las Agrupaciones (para modificar)"

        # Mostrar la lista de agrupaciones
        print(f"\n--- {titulo} ---")
        for i, agrup in enumerate(agrupaciones_a_mostrar):
            print(f"{i + 1}. {agrup['agrupacion']}")
        
        # Pedir al usuario que elija
        try:
            seleccion_str = input(f"\nSeleccione el número de la agrupación (o 'q' para salir): ")
            if seleccion_str.lower() == 'q':
                break
            
            indice_seleccionado = int(seleccion_str) - 1
            if not 0 <= indice_seleccionado < len(agrupaciones_a_mostrar):
                print("❌ Número fuera de rango. Intente de nuevo.")
                continue

            # Encontrar el objeto correcto en la lista original de 'datos'
            agrupacion_a_editar = agrupaciones_a_mostrar[indice_seleccionado]

            # Pedir el nombre del docente
            print(f"\nEditando: '{agrupacion_a_editar['agrupacion']}'")
            docente_actual = agrupacion_a_editar.get('docente_asignado') or "Ninguno"
            print(f"Docente actual: {docente_actual}")
            
            nuevo_docente = input("Ingrese el nombre completo del nuevo docente (o Enter para cancelar): ")
            
            if nuevo_docente.strip():
                agrupacion_a_editar['docente_asignado'] = nuevo_docente.strip()
                guardar_datos(datos)
            else:
                print("Asignación cancelada.")

        except ValueError:
            print("❌ Entrada no válida. Por favor, ingrese un número.")
            continue
        
        continuar = input("\n¿Desea realizar otra asignación/modificación? (s/n): ").lower()
        if continuar != 's':
            break

    print("\n--- Fin del programa. ---")

if __name__ == "__main__":
    main()
