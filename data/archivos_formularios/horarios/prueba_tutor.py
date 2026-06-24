# -*- coding: utf-8 -*-
import pandas as pd
import re
import os
from pathlib import Path

def limpiar_texto(texto):
    """Limpia espacios y normaliza texto."""
    if pd.isna(texto): return ""
    return str(texto).strip()

def extraer_tutor_exacto(ruta_archivo, nombre_hoja):
    """Busca la celda con la palabra 'TUTOR' y extrae el valor de la derecha."""
    print(f"\n--- Analizando hoja: {nombre_hoja} ---")
    
    try:
        # Leemos el Excel sin encabezados para tener una matriz pura de datos
        df = pd.read_excel(ruta_archivo, sheet_name=nombre_hoja, header=None, engine='openpyxl')
        
        tutor_encontrado = "NO ENCONTRADO"
        
        # Recorremos todas las celdas buscando la palabra clave "TUTOR"
        for rowIndex, row in df.iterrows():
            for colIndex, cellValue in row.items():
                
                texto_celda = limpiar_texto(cellValue).upper()
                
                # Verificamos si la celda contiene la palabra "TUTOR"
                # Usamos una validación estricta para evitar falsos positivos
                if "TUTOR" in texto_celda: 
                    print(f"   > Palabra 'TUTOR' encontrada en Fila {rowIndex}, Columna {colIndex}")
                    
                    # Intentamos obtener el valor de la celda de la derecha (colIndex + 1)
                    # Si esa está vacía, probamos la siguiente (por si hay celdas combinadas vacías en medio)
                    for offset in range(1, 5): # Buscamos hasta 4 celdas a la derecha
                        if colIndex + offset < len(df.columns):
                            posible_nombre = limpiar_texto(df.iloc[rowIndex, colIndex + offset])
                            
                            if posible_nombre and posible_nombre.upper() != "TUTOR": # Si tiene texto y no es la palabra tutor repetida
                                # Limpieza del nombre (quitar títulos Lic., Mgs., etc.)
                                nombre_limpio = re.sub(r'^(LIC\.?|TG\.?|MGS\.?|DR\.?|MSC\.?|PROF\.?)\s*', '', posible_nombre, flags=re.IGNORECASE)
                                tutor_encontrado = nombre_limpio.strip().title()
                                print(f"   ✅ ¡Tutor extraído!: {tutor_encontrado} (estaba en columna {colIndex + offset})")
                                return tutor_encontrado
        
        if tutor_encontrado == "NO ENCONTRADO":
            print("   ❌ No se encontró la etiqueta 'TUTOR' o la celda adyacente estaba vacía.")
            
        return tutor_encontrado

    except Exception as e:
        print(f"   ❌ Error leyendo la hoja: {e}")
        return None

# ==========================================
# BLOQUE PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("🔍 PRUEBA DE EXTRACCIÓN DE TUTOR (Versión Mejorada)")
    
    # 1. Pide la ruta (acepta carpetas o archivos)
    ruta_input = input("Arrastra el archivo Excel o escribe '.' para buscar en esta carpeta: ").strip()
    ruta_input = ruta_input.replace("'", "").replace('"', '') # Limpiar comillas

    archivo_seleccionado = None

    # Si es una carpeta o el punto '.', buscamos archivos
    if os.path.isdir(ruta_input) or ruta_input == '.':
        if ruta_input == '.': ruta_input = os.getcwd()
        
        archivos = [f for f in os.listdir(ruta_input) if f.endswith(('.xlsx', '.xls')) and not f.startswith('~$')]
        
        if not archivos:
            print("❌ No se encontraron archivos Excel en esa carpeta.")
            exit()
            
        print(f"\n📚 Archivos encontrados:")
        for i, f in enumerate(archivos, 1):
            print(f"  [{i}] {f}")
            
        seleccion = input("\nElige el número del archivo: ").strip()
        try:
            archivo_seleccionado = os.path.join(ruta_input, archivos[int(seleccion)-1])
        except:
            print("❌ Selección inválida.")
            exit()
    
    # Si es un archivo directo
    elif os.path.isfile(ruta_input):
        archivo_seleccionado = ruta_input
    else:
        print("❌ La ruta no existe.")
        exit()

    print(f"\n📄 Procesando: {os.path.basename(archivo_seleccionado)}")
    
    try:
        xls = pd.ExcelFile(archivo_seleccionado, engine='openpyxl')
        # 2. Procesa todas las hojas
        for hoja in xls.sheet_names:
            extraer_tutor_exacto(archivo_seleccionado, hoja)
    except Exception as e:
        print(f"❌ Error crítico abriendo el archivo: {e}")