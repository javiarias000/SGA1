# -*- coding: utf-8 -*-
import pandas as pd
import re
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple, List
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
    DIAS = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES']
    # Palabras clave para buscar en el encabezado
    KEY_CURSO = ['CURSO', 'AÑO', 'GRADO', 'NIVEL']
    KEY_TUTOR = ['TUTOR', 'DOCENTE TUTOR', 'TUTOR/A']

# =============================================================================
# HERRAMIENTAS DE LIMPIEZA
# =============================================================================
def limpiar_texto(texto: str) -> str:
    """Limpia el texto de celdas (NaN, saltos de línea, espacios extra)."""
    if pd.isna(texto): return ""
    # Quitar saltos de línea, comas y normalizar espacios
    return re.sub(r'\s+', ' ', str(texto).replace('\n', ' ').replace(',', ' ')).strip()

def normalizar_nombre(texto: str) -> str:
    """Elimina títulos académicos y formatea el nombre/curso."""
    if not texto: return "ND"
    TITLES_REGEX = r'^(LIC\.?|TG\.?|MGS\.?|DR\.?|MSC\.?|PROF\.?|ING\.?|TSU\.?)\s*'
    texto_limpio = re.sub(TITLES_REGEX, '', texto, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', texto_limpio).strip().title()

# =============================================================================
# LÓGICA DE EXTRACCIÓN (METADATOS Y HORARIO)
# =============================================================================
class ProcesadorHorario:
    
    def buscar_dato_por_etiqueta(self, df_area: pd.DataFrame, keywords: list, filas_limite: int = 6) -> str:
        """Busca una keyword en un área definida y devuelve el valor de la celda adyacente."""
        df_head = df_area.head(filas_limite)
        
        for rowIndex in range(len(df_head)):
            for colIndex in range(len(df_head.columns)):
                cellValue = df_head.iloc[rowIndex, colIndex]
                texto_celda = limpiar_texto(cellValue).upper()
                
                if any(k in texto_celda for k in keywords):
                    for offset in range(1, 5):
                        if colIndex + offset < len(df_head.columns):
                            valor = limpiar_texto(df_head.iloc[rowIndex, colIndex + offset])
                            if valor and valor.upper() not in texto_celda:
                                return valor
        return "ND"
        
    def normalizar_curso_paralelo(self, curso_raw_value: str, hoja_default: str) -> Tuple[str, str]:
        """Procesa el valor crudo del curso para separar el paralelo."""
        curso_completo = curso_raw_value.strip().upper() if curso_raw_value != "ND" else hoja_default.strip().upper()
        curso = curso_completo
        paralelo = 'ND'
        
        match_paralelo = re.search(r'([A-ZÍÓÚÜ\s\d]+)\s+([A-Z\d])$', curso_completo)
        if match_paralelo:
            curso = match_paralelo.group(1).strip()
            paralelo = match_paralelo.group(2).strip()
            
        return normalizar_nombre(curso), paralelo

    def descomponer_celda_clase(self, contenido: str) -> Dict[str, str]:
        """Extrae Asignatura, Docente y Aula de una celda de horario."""
        res = {'asignatura': 'ND', 'docente': 'ND', 'aula': 'ND'}
        if not contenido: return res
        
        texto = contenido.strip()
        
        # 1. Extraer AULA/BLOQUE (Suele estar al final)
        match_aula = re.search(r'(sala|salón|bloque|lab)\s*.*$', texto, flags=re.IGNORECASE)
        if match_aula:
            aula_info = match_aula.group(0).strip()
            res['aula'] = normalizar_nombre(aula_info)
            texto = texto.replace(aula_info, '').strip()
            
        # 2. Extraer DOCENTE y ASIGNATURA
        TITLES_REGEX = r'(Lic\.?|Tg\.?|Mgs\.?|Dr\.?|Prof\.?|Ing\.?|Msc\.?)\s*'
        match_docente = re.search(TITLES_REGEX + r'([A-Za-zÁÉÍÓÚñÑ\s\.]+)', texto, flags=re.IGNORECASE)
        
        if match_docente:
            raw_docente = match_docente.group(0)
            res['docente'] = normalizar_nombre(raw_docente)
            
            asignatura_raw = texto.split(raw_docente)[0]
            res['asignatura'] = normalizar_nombre(asignatura_raw)
        else:
            res['asignatura'] = normalizar_nombre(texto)
            
        return res

    def procesar_documento_completo(self, archivo: str) -> List[Dict[str, str]]:
        """Busca y procesa dinámicamente bloques de horario en una hoja (horizontal y vertical)."""
        all_registros = []
        
        try:
            xls = pd.ExcelFile(archivo, engine='openpyxl')
            hoja_principal = xls.sheet_names[0] 
            df_raw = pd.read_excel(archivo, sheet_name=hoja_principal, header=None, engine='openpyxl')
        except Exception as e:
            logger.error(f"❌ Error al leer el archivo {archivo}: {e}")
            return []

        # 1. Escanear DF para encontrar todas las etiquetas clave 'TUTOR' (inicio de bloque)
        tutor_coords = [] # Almacenará tuplas (fila, columna)
        
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

            logger.info(f"--- Procesando Bloque {i+1} --- (R:{start_row}-{end_row-1}, C:{start_col}-{end_col-1})")
            
            # 4. EXTRAER METADATOS DEL BLOQUE
            df_metadata_area = df_raw.iloc[start_row:start_row + 5, start_col:min(end_col, start_col + 10)].copy()

            tutor_raw_value = self.buscar_dato_por_etiqueta(df_metadata_area, Config.KEY_TUTOR)
            curso_raw_value = self.buscar_dato_por_etiqueta(df_metadata_area, Config.KEY_CURSO)
            
            curso, paralelo = self.normalizar_curso_paralelo(curso_raw_value, hoja_principal)
            tutor = normalizar_nombre(tutor_raw_value)
            
            if curso == 'Nd' and tutor == 'Nd':
                 logger.warning("   ⚠️ No se pudieron extraer metadatos válidos. Saltando bloque.")
                 continue

            logger.info(f"   > Curso: {curso} | Paralelo: {paralelo} | Tutor: {tutor}")

            # 5. ENCONTRAR LA TABLA DE HORARIOS DENTRO DEL BLOQUE
            start_grid_row_index = -1
            col_map = {}
            
            df_block_area = df_raw.iloc[start_row: end_row, start_col: end_col].copy()
            
            for idx_block, row in df_block_area.iterrows():
                row_slice = row[start_col: end_col]
                row_str = row_slice.astype(str).str.upper().tolist()
                
                if "HORA" in str(row_str) and "LUNES" in str(row_str):
                    start_grid_row_index = idx_block 
                    
                    for col_idx, val in row_slice.items():
                        val_str = limpiar_texto(val).upper()
                        if "HORA" in val_str: col_map['HORA'] = col_idx
                        for dia in Config.DIAS:
                            if dia in val_str: col_map[dia] = col_idx
                    break
            
            if start_grid_row_index == -1 or not col_map:
                logger.warning("   ⚠️ No se encontró la cuadrícula de horarios dentro del bloque. Saltando.")
                continue
                
            # 6. PROCESAR EL GRID
            df_grid = df_raw.iloc[start_grid_row_index + 1: end_row].copy()
            
            for _, row in df_grid.iterrows():
                idx_hora = col_map.get('HORA')
                rango_hora = limpiar_texto(row[idx_hora]) if idx_hora is not None else ""
                
                if not rango_hora or ":" not in rango_hora: continue

                for dia in Config.DIAS:
                    idx_dia = col_map.get(dia)
                    if idx_dia is not None and idx_dia >= start_col and idx_dia < end_col:
                        
                        contenido = limpiar_texto(row[idx_dia])
                        
                        if contenido:
                            detalles = self.descomponer_celda_clase(contenido)
                            
                            if detalles['asignatura'] != 'Nd' or detalles['docente'] != 'Nd':
                                all_registros.append({
                                    'curso': curso,
                                    'paralelo': paralelo,
                                    'tutor': tutor,
                                    'dia': dia,
                                    'hora': rango_hora,
                                    'asignatura': detalles['asignatura'],
                                    'docente_clase': detalles['docente'],
                                    'aula': detalles['aula'],
                                    'origen': hoja_principal
                                })

        return all_registros

# =============================================================================
# MAIN
# =============================================================================
def main():
    print("🚀 INICIANDO ANÁLISIS DE HORARIOS Y TUTORES\n")
    
    ruta_input = input("Escribe la ruta del archivo o '.' para buscar en esta carpeta: ").strip()
    ruta_input = ruta_input.replace("'", "").replace('"', '')
    
    archivo = None
    
    if ruta_input == '.':
        archivos = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$')]
        if archivos:
            print("\nArchivos encontrados:")
            for i, f in enumerate(archivos): print(f"[{i+1}] {f}")
            sel = int(input("Selecciona número: ")) - 1
            archivo = archivos[sel]
        else:
            print("No hay excels aquí.")
            return
    elif os.path.isfile(ruta_input):
        archivo = ruta_input
    else:
        print("Ruta inválida.")
        return

    print(f"\n📄 Procesando archivo: {archivo}")
    
    try:
        pd.ExcelFile(archivo, engine='openpyxl') 
    except Exception as e:
        print(f"❌ Error al abrir el archivo: {e}")
        return
        
    procesador = ProcesadorHorario()
    todos_los_datos = procesador.procesar_documento_completo(archivo)
    
    # Exportar
    if todos_los_datos:
        df_final = pd.DataFrame(todos_los_datos)
        
        # --- 1. ARCHIVO DE TUTORES Y CURSOS ---
        df_tutores = df_final[['curso', 'paralelo', 'tutor']].drop_duplicates().sort_values(['curso', 'paralelo'])
        
        nombre_salida_tutores = f"REPORTE_TUTORES_CURSOS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_tutores.to_csv(nombre_salida_tutores, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"\n✅ EXPORTACIÓN 1: Tutores y Cursos")
        print(f"   Archivo: {nombre_salida_tutores}")
        print(f"   Registros únicos: {len(df_tutores)}")
        
        # --- 2. ARCHIVO DE DOCENTES Y HORARIOS ---
        # Columnas solicitadas: materias, agrupaciones (asignatura), docentes, hora
        df_horarios = df_final[['curso', 'paralelo', 'dia', 'hora', 'asignatura', 'docente_clase', 'aula']].copy()
        
        nombre_salida_horarios = f"REPORTE_DOCENTES_HORARIOS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_horarios.to_csv(nombre_salida_horarios, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"\n✅ EXPORTACIÓN 2: Docentes y Horarios")
        print(f"   Archivo: {nombre_salida_horarios}")
        print(f"   Total registros de clases: {len(df_horarios)}")
        
        # Mostrar resumen consolidado
        print("\n📝 RESUMEN DE CURSOS Y TUTORES ÚNICOS EXTRAÍDOS:")
        print(df_tutores.to_string(index=False))
        
    else:
        print("\n⚠️ No se extrajeron datos de horarios o tutores.")

if __name__ == "__main__":
    main()