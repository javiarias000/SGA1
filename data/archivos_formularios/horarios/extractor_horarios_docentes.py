# -*- coding: utf-8 -*-
"""
Script de Extracción de Horarios y Docentes V7.0 - Estructura de Bloques Independientes
Autor: Analista de Datos Experto.
Análisis Visual: Se detectó que cada bloque (A, B, C) tiene su propia columna de HORA y DÍAS.
Estrategia: 
1. Detectar anclajes de 'CURSO'.
2. Definir el área del bloque.
3. Buscar localmente la fila de encabezados (LUNES, MARTES) y la columna HORA dentro de ese bloque.
4. Separar Materia y Docente usando los prefijos de título.
"""
import pandas as pd
import re
import os
import logging
from datetime import datetime
from typing import Dict, Tuple, List, Optional
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Config:
    DIAS = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES']
    KEY_CURSO = ['CURSO', 'AÑO', 'GRADO', 'NIVEL', 'BACHILLERATO', 'BASICA']
    # Patrones para detectar cursos si falta la etiqueta
    PATRONES_NIVEL = [
        'PRIMERO', 'SEGUNDO', 'TERCERO', 'CUARTO', 'QUINTO', 
        'SEXTO', 'SEPTIMO', 'OCTAVO', 'NOVENO', 'DECIMO', 
        'BGU', 'EGB'
    ]
    KEY_TUTOR = ['TUTOR', 'DOCENTE TUTOR', 'TUTOR/A']
    KEY_HORA = ['HORA', 'HORARIO'] 

# =============================================================================
# HERRAMIENTAS DE LIMPIEZA
# =============================================================================
def limpiar_texto(texto: str) -> str:
    if pd.isna(texto): return "ND"
    # Reemplazar saltos de línea por espacios para facilitar regex
    return re.sub(r'\s+', ' ', str(texto).replace('\n', ' ')).strip()

def normalizar_nombre(texto: str) -> str:
    if not texto or texto.upper() == 'ND': return "ND"
    # Eliminar títulos al inicio para limpiar el nombre
    TITLES_REGEX = r'^(LIC\.?|TG\.?|MGS\.?|DR\.?|MSC\.?|PROF\.?|ING\.?|TSU\.?|TEG\.?)\s*'
    texto_limpio = re.sub(TITLES_REGEX, '', texto, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', texto_limpio).strip().title()

def normalizar_curso_paralelo(curso_raw_value: str) -> Tuple[str, str]:
    if curso_raw_value == "ND": return "ND", "ND"
    curso_completo = curso_raw_value.strip().upper()
    
    # Patrón: "PRIMERO A" -> Curso: PRIMERO, Paralelo: A
    match_paralelo = re.search(r'(.+?)\s+([A-Z\d])$', curso_completo)
    if match_paralelo:
        return normalizar_nombre(match_paralelo.group(1)), match_paralelo.group(2).strip()
    
    return normalizar_nombre(curso_completo), 'ND'

def descomponer_celda_clase(contenido: str) -> Dict[str, str]:
    """
    Separa la materia del docente basándose en los títulos académicos.
    Ej: "Coro Lic. Juan Perez" -> Materia: Coro, Docente: Juan Perez
    """
    res = {'asignatura': 'ND', 'docente_clase': 'ND', 'aula': 'ND'}
    texto = limpiar_texto(contenido)
    if texto == 'ND': return res
    
    # 1. Extraer Aula/Bloque/Sala (generalmente al final)
    match_aula = re.search(r'(sala|salón|bloque|lab)\s*.*$', texto, flags=re.IGNORECASE)
    if match_aula:
        res['aula'] = normalizar_nombre(match_aula.group(0))
        texto = texto.replace(match_aula.group(0), '').strip()
        
    # 2. Separar Materia y Docente usando Títulos
    # Buscamos: (Título) (Nombre)
    TITLES_REGEX = r'(Lic\.?|Tg\.?|Mgs\.?|Dr\.?|Prof\.?|Ing\.?|Msc\.?|Teg\.?)\s+'
    match_docente = re.search(TITLES_REGEX + r'([A-Za-zÁÉÍÓÚñÑ\s\.]+)', texto, flags=re.IGNORECASE)
    
    if match_docente:
        # Encontramos un docente con título
        raw_docente = match_docente.group(0).strip() # Ej: "Lic. Juan Perez"
        res['docente_clase'] = normalizar_nombre(raw_docente) # Ej: "Juan Perez"
        
        # La materia es lo que está antes del título
        partes = texto.split(raw_docente)
        if len(partes) > 0:
            res['asignatura'] = normalizar_nombre(partes[0])
    else:
        # Si no hay título, asumimos que todo es la materia (o el nombre del docente si es una celda rara)
        # Para ser seguros, lo ponemos en asignatura, pero marcamos docente como ND
        res['asignatura'] = normalizar_nombre(texto)

    return res

# =============================================================================
# PROCESADOR CENTRAL
# =============================================================================
class ProcesadorHorariosV7:
    
    def encontrar_anclajes(self, df_raw: pd.DataFrame) -> List[Tuple[int, int, str]]:
        """Escanea todo el documento buscando celdas que parezcan encabezados de curso."""
        anchors = []
        # Escaneamos un número razonable de filas, o todo el documento si es necesario
        rows_to_scan = len(df_raw) 
        
        for r in range(rows_to_scan):
            for c in range(len(df_raw.columns)):
                val = limpiar_texto(df_raw.iloc[r, c]).upper()
                
                es_anclaje = False
                valor_curso = "ND"
                
                # Caso A: Etiqueta "CURSO"
                if any(k == val for k in Config.KEY_CURSO): # Coincidencia exacta o muy cercana
                    # El valor suele estar a la derecha
                    if c + 1 < len(df_raw.columns):
                        vecino = limpiar_texto(df_raw.iloc[r, c+1])
                        if len(vecino) > 3:
                            valor_curso = vecino
                            es_anclaje = True
                
                # Caso B: La celda contiene directamente el curso (Ej: "PRIMERO A")
                elif any(pat in val for pat in Config.PATRONES_NIVEL) and len(val) < 50:
                    # Validar que no sea un texto largo de contenido
                    valor_curso = val
                    es_anclaje = True
                
                if es_anclaje:
                    # Evitar duplicados cercanos (mismo bloque detectado varias veces)
                    if not any(abs(a[0]-r) < 5 and abs(a[1]-c) < 5 for a in anchors):
                        anchors.append((r, c, valor_curso))
                        logger.info(f"   📍 Bloque detectado en R{r}, C{c}: {valor_curso}")
        
        # Ordenar por fila y luego columna
        return sorted(anchors, key=lambda x: (x[0], x[1]))

    def procesar_hoja(self, archivo: str) -> Tuple[List[dict], List[dict]]:
        registros_horarios = []
        registros_tutores = []
        
        try:
            xls = pd.ExcelFile(archivo, engine='openpyxl')
            hoja = xls.sheet_names[0]
            df = pd.read_excel(archivo, sheet_name=hoja, header=None, engine='openpyxl')
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return [], []

        anchors = self.encontrar_anclajes(df)
        
        if not anchors:
            logger.error("No se encontraron bloques de cursos.")
            return [], []

        for i, (r_start, c_start, raw_curso) in enumerate(anchors):
            # 1. Definir límites del bloque actual
            # Límite vertical: hasta el siguiente anclaje que esté más abajo
            r_end = len(df)
            # Límite horizontal: hasta el siguiente anclaje que esté a la derecha (en la misma franja de filas)
            c_end = len(df.columns)
            
            for next_r, next_c, _ in anchors:
                if next_r > r_start and next_r < r_end:
                    r_end = next_r
                if next_r == r_start and next_c > c_start and next_c < c_end:
                    c_end = next_c
            
            # Ajuste fino: A veces el siguiente bloque vertical está mucho más abajo,
            # pero el bloque actual horizontalmente tiene un límite claro.
            # Asumiremos un ancho máximo de ~10 columnas si no hay otro bloque a la derecha.
            if c_end == len(df.columns) and (c_end - c_start) > 15:
                c_end = c_start + 10 

            logger.info(f"--- Procesando Bloque {raw_curso} (R:{r_start}-{r_end}, C:{c_start}-{c_end}) ---")
            
            # 2. Extraer Metadatos (Tutor)
            # Buscamos "Tutor" en las primeras filas del bloque
            tutor = "ND"
            curso, paralelo = normalizar_curso_paralelo(raw_curso)
            
            df_bloque_meta = df.iloc[r_start:r_start+5, c_start:c_end]
            
            for br in range(len(df_bloque_meta)):
                for bc in range(len(df_bloque_meta.columns)):
                    val = limpiar_texto(df_bloque_meta.iloc[br, bc]).upper()
                    if any(k in val for k in Config.KEY_TUTOR):
                        # Buscar valor a la derecha
                        if bc + 1 < len(df_bloque_meta.columns):
                            t_val = limpiar_texto(df_bloque_meta.iloc[br, bc+1])
                            if len(t_val) > 3:
                                tutor = normalizar_nombre(t_val)
            
            registros_tutores.append({'curso': curso, 'paralelo': paralelo, 'tutor': tutor})

            # 3. Encontrar Cuadrícula LOCALMENTE
            # Buscamos la fila de encabezados (LUNES, MARTES) DENTRO de este bloque
            df_bloque = df.iloc[r_start:r_end, c_start:c_end]
            
            header_row_idx = -1
            col_map = {}
            
            for br, row in df_bloque.iterrows():
                row_vals = [limpiar_texto(v).upper() for v in row]
                # Si la fila tiene al menos 3 días de la semana, es el encabezado
                matches = sum(1 for d in Config.DIAS if any(d in rv for rv in row_vals))
                
                if matches >= 3:
                    header_row_idx = br
                    # Mapear columnas
                    for bc, val in enumerate(row): # bc es relativo al bloque slice, cuidado
                        val_u = limpiar_texto(val).upper()
                        real_col_idx = df_bloque.columns[bc] # Índice real en el DF original
                        
                        for d in Config.DIAS:
                            if d in val_u: col_map[d] = real_col_idx
                        
                        if any(k in val_u for k in Config.KEY_HORA):
                            col_map['HORA'] = real_col_idx
                    break
            
            if header_row_idx == -1:
                logger.warning(f"   ⚠️ No se encontró cuadrícula de horarios para {curso} {paralelo}")
                continue
                
            if 'HORA' not in col_map:
                # Si no se encontró columna HORA explícita, asumimos la primera columna del bloque
                # o la columna anterior a LUNES
                if 'LUNES' in col_map:
                    col_map['HORA'] = col_map['LUNES'] - 1
                    logger.info("   ℹ️ Columna HORA inferida (a la izquierda de Lunes)")
                else:
                    logger.warning("   ⚠️ Falta columna HORA crítica.")
                    continue

            # 4. Extraer Clases
            # Iteramos desde la fila siguiente al encabezado hasta el fin del bloque
            for r_data in range(header_row_idx + 1, r_end):
                if r_data not in df.index: break
                
                hora_val = limpiar_texto(df.iloc[r_data, col_map['HORA']])
                
                # Validar que sea una fila de hora (tiene números y ':' o '-')
                if not (re.search(r'\d', hora_val) and (':' in hora_val or '-' in hora_val or 'A' in hora_val.upper())):
                    continue
                
                for dia in Config.DIAS:
                    if dia in col_map:
                        contenido = limpiar_texto(df.iloc[r_data, col_map[dia]])
                        if len(contenido) > 3: # Celda no vacía
                            detalles = descomponer_celda_clase(contenido)
                            
                            registros_horarios.append({
                                'curso': curso,
                                'paralelo': paralelo,
                                'dia': dia,
                                'hora': hora_val,
                                'asignatura': detalles['asignatura'],
                                'docente': detalles['docente_clase'],
                                'aula': detalles['aula']
                            })
                            
            logger.info(f"   ✅ Horario extraído para {curso} {paralelo}")

        return registros_horarios, registros_tutores

# =============================================================================
# MAIN
# =============================================================================
def main():
    print("🚀 EXTRACTOR DE HORARIOS V7 (Bloques Independientes) 🚀")
    
    ruta_input = input("Archivo o carpeta (.): ").strip().replace("'", "").replace('"', '')
    archivo = None
    
    if ruta_input == '.':
        archivos = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$')]
        if archivos:
            for i, f in enumerate(archivos): print(f"[{i+1}] {f}")
            archivo = archivos[int(input("Opción: ")) - 1]
    elif os.path.isfile(ruta_input):
        archivo = ruta_input
        
    if not archivo: return

    procesador = ProcesadorHorariosV7()
    datos_horarios, datos_tutores = procesador.procesar_hoja(archivo)
    
    if datos_horarios:
        df_h = pd.DataFrame(datos_horarios)
        file_h = f"REPORTE_DOCENTES_HORARIOS_{datetime.now().strftime('%H%M')}.csv"
        df_h.to_csv(file_h, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n✅ Horarios guardados en: {file_h} ({len(df_h)} regs)")
        print(df_h.head(3).to_string())

    if datos_tutores:
        df_t = pd.DataFrame(datos_tutores)
        file_t = f"REPORTE_TUTORES_{datetime.now().strftime('%H%M')}.csv"
        df_t.to_csv(file_t, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n✅ Tutores guardados en: {file_t} ({len(df_t)} regs)")
        print(df_t.to_string())

if __name__ == "__main__":
    main()