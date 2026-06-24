# -*- coding: utf-8 -*-
import pandas as pd
import re
import os
import logging
from datetime import datetime
from typing import Dict, Tuple, List
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN Y LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Config:
    # Palabras clave para buscar en el encabezado
    KEY_CURSO = ['CURSO', 'AÑO', 'GRADO', 'NIVEL', 'BACHILLERATO']
    KEY_TUTOR = ['TUTOR', 'DOCENTE TUTOR', 'TUTOR/A']

# =============================================================================
# HERRAMIENTAS DE LIMPIEZA
# =============================================================================
def limpiar_texto(texto: str) -> str:
    """Limpia el texto de celdas (NaN, saltos de línea, espacios extra)."""
    if pd.isna(texto): return "ND" 
    # Normalizar espacios y eliminar saltos de línea/comas
    texto_limpio = re.sub(r'\s+', ' ', str(texto).replace('\n', ' ').replace(',', ' ')).strip()
    return texto_limpio

def normalizar_nombre(texto: str) -> str:
    """Elimina títulos académicos y formatea el nombre/curso."""
    if not texto or texto.upper() == 'ND': return "ND"
    TITLES_REGEX = r'^(LIC\.?|TG\.?|MGS\.?|DR\.?|MSC\.?|PROF\.?|ING\.?|TSU\.?)\s*'
    texto_limpio = re.sub(TITLES_REGEX, '', texto, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', texto_limpio).strip().title()

# =============================================================================
# LÓGICA DE EXTRACCIÓN DE METADATOS
# =============================================================================
class ExtractorMetadatosBloque:
    
    def buscar_dato_por_etiqueta(self, df_area: pd.DataFrame, keywords: list, filas_limite: int = 6) -> str:
        """Busca una keyword en un área definida y devuelve el valor de la celda adyacente."""
        df_head = df_area.head(filas_limite)
        
        for rowIndex in range(len(df_head)):
            for colIndex in range(len(df_head.columns)):
                cellValue = df_head.iloc[rowIndex, colIndex]
                texto_celda = limpiar_texto(cellValue).upper()
                
                if any(k in texto_celda for k in keywords):
                    # Búsqueda en celdas de la derecha
                    for offset in range(1, 5):
                        if colIndex + offset < len(df_head.columns):
                            valor = limpiar_texto(df_head.iloc[rowIndex, colIndex + offset])
                            
                            # CORRECCIÓN CLAVE: El valor debe ser no vacío y tener al menos 3 caracteres
                            if valor != "ND" and len(valor) > 2 and valor.upper() not in texto_celda:
                                return valor
        return "ND"
        
    def normalizar_curso_paralelo(self, curso_raw_value: str) -> Tuple[str, str]:
        """Procesa el valor crudo del curso para separar el paralelo (A, B, C, etc.)."""
        
        if curso_raw_value == "ND":
            return "ND", "ND"
            
        curso_completo = curso_raw_value.strip().upper()
        curso = curso_completo
        paralelo = 'ND'
        
        # Patrón mejorado para separar el curso del paralelo al final de la celda.
        # Captura todo el texto antes del último espacio, si lo último es una letra/dígito (A, B, C, 1, 2)
        match_paralelo = re.search(r'(.+?)\s+([A-Z\d])$', curso_completo)
        
        if match_paralelo:
            curso = match_paralelo.group(1).strip()
            paralelo = match_paralelo.group(2).strip()
            
        return normalizar_nombre(curso), paralelo

    def procesar_hoja_completa(self, archivo: str) -> List[Dict[str, str]]:
        """Busca y extrae metadatos de bloques distribuidos horizontal y verticalmente."""
        metadatos_bloques = []
        
        try:
            xls = pd.ExcelFile(archivo, engine='openpyxl')
            hoja_principal = xls.sheet_names[0] 
            df_raw = pd.read_excel(archivo, sheet_name=hoja_principal, header=None, engine='openpyxl')
        except Exception as e:
            logger.error(f"❌ Error al leer el archivo {archivo}: {e}")
            return []

        # 1. Escanear DF para encontrar todas las etiquetas clave 'TUTOR' (inicio de bloque)
        tutor_coords = []
        
        for rowIndex in range(len(df_raw)):
            for colIndex in range(len(df_raw.columns)):
                cellValue = df_raw.iloc[rowIndex, colIndex]
                texto_celda = limpiar_texto(cellValue).upper()
                
                if any(k in texto_celda for k in Config.KEY_TUTOR):
                    tutor_coords.append((rowIndex, colIndex))
        
        if not tutor_coords:
            logger.error("❌ No se encontraron anclajes de Tutor en el documento. No se puede definir bloques.")
            return []

        # 2. Ordenar las coordenadas para definir los límites de los bloques
        tutor_coords.sort(key=lambda x: (x[0], x[1]))
        
        bloques_unicos = set()

        # 3. Procesar cada bloque encontrado (ventanas)
        for i, (start_row, start_col) in enumerate(tutor_coords):
            
            end_row = len(df_raw)
            end_col = len(df_raw.columns)
            
            # Buscamos el siguiente punto de inicio (vertical o horizontal) para definir los límites
            for j in range(i + 1, len(tutor_coords)):
                next_row, next_col = tutor_coords[j]
                
                if next_row == start_row:
                    end_col = next_col
                
                if next_row > start_row:
                    end_row = next_row 
                    break

            # ÁREA DE BÚSQUEDA DE METADATOS: 5 filas antes (para el curso) y 5 filas después del tutor.
            metadata_start_row = max(0, start_row - 5) 
            
            logger.info(f"--- Buscando metadatos en R:{metadata_start_row}-{start_row+4}, C:{start_col}-{min(end_col, start_col + 10)-1} ---")
            
            # 4. EXTRAER METADATOS DEL BLOQUE
            # Área de búsqueda: 10 filas x 10 columnas desde el inicio del bloque
            df_metadata_area = df_raw.iloc[metadata_start_row:start_row + 5, start_col:min(end_col, start_col + 10)].copy()

            tutor_raw_value = self.buscar_dato_por_etiqueta(df_metadata_area, Config.KEY_TUTOR)
            curso_raw_value = self.buscar_dato_por_etiqueta(df_metadata_area, Config.KEY_CURSO)
            
            curso, paralelo = self.normalizar_curso_paralelo(curso_raw_value)
            tutor = normalizar_nombre(tutor_raw_value)
            
            bloque_key = (curso, paralelo, tutor)

            if curso == 'ND' or paralelo == 'ND' or tutor == 'ND':
                 logger.warning(f"   ⚠️ Bloque en R{start_row}, C{start_col} incompleto: {bloque_key}. Saltando.")
                 continue
            
            if bloque_key not in bloques_unicos:
                bloques_unicos.add(bloque_key)
                logger.info(f"   ✅ Bloque encontrado: {curso} {paralelo} - Tutor: {tutor}")
                
                metadatos_bloques.append({
                    'curso': curso,
                    'paralelo': paralelo,
                    'tutor': tutor,
                    'origen_fila': start_row,
                    'origen_columna': start_col,
                    'documento_origen': os.path.basename(archivo)
                })

        return metadatos_bloques

# =============================================================================
# MAIN EXECUTION
# =============================================================================
def main():
    print("🔬 EXTRACTOR DE METADATOS DE BLOQUES (Curso, Tutor, Paralelo) 🔍")
    
    ruta_input = input("Escribe la ruta del archivo o '.' para buscar en esta carpeta: ").strip()
    ruta_input = ruta_input.replace("'", "").replace('"', '')
    
    archivo = None
    
    if ruta_input == '.':
        archivos = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$')]
        if archivos:
            print("\n📚 Archivos encontrados:")
            for i, f in enumerate(archivos): print(f"  [{i+1}] {f}")
            sel = int(input("Elige el número del archivo: ")) - 1
            archivo = archivos[sel]
        else:
            print("No hay excels aquí.")
            return
    elif os.path.isfile(ruta_input):
        archivo = ruta_input
    else:
        print("Ruta inválida.")
        return

    print(f"\n📄 Analizando: {os.path.basename(archivo)}")
    
    try:
        pd.ExcelFile(archivo, engine='openpyxl') 
    except Exception as e:
        print(f"❌ Error al abrir el archivo: {e}")
        return
        
    extractor = ExtractorMetadatosBloque()
    datos_extraidos = extractor.procesar_hoja_completa(archivo)
    
    if datos_extraidos:
        df_final = pd.DataFrame(datos_extraidos)
        
        df_reporte = df_final[['curso', 'paralelo', 'tutor']].drop_duplicates().sort_values(['curso', 'paralelo'])
        
        nombre_salida = f"REPORTE_TUTORES_CURSOS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_reporte.to_csv(nombre_salida, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"\n✅ ¡ÉXITO! Se encontraron {len(df_reporte)} cursos/paralelos únicos.")
        print(f"   Archivo de tutores guardado: {nombre_salida}")
        
        print("\n📝 LISTADO DE TUTORES Y CURSOS EXTRAÍDOS:")
        print(df_reporte.to_string(index=False))
        
    else:
        print("\n⚠️ No se pudieron extraer metadatos de ningún bloque. Verifica las etiquetas 'TUTOR' y 'CURSO'.")

if __name__ == "__main__":
    main()