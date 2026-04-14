# -*- coding: utf-8 -*- 
import pandas as pd
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import unicodedata

# =============================================================================
# CONFIGURACIÓN Y LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'analisis_horarios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CLASES AUXILIARES DE LIMPIEZA
# =============================================================================
class DataCleaner:
    @staticmethod
    def normalizar_texto(texto: str, titulo: bool = False) -> str:
        """Normaliza texto general (quita espacios extra, opcionalmente a título)"""
        if pd.isna(texto) or texto == '': return ''
        texto = str(texto).strip()
        texto = re.sub(r'\s+', ' ', texto)
        if titulo: texto = texto.title()
        return texto

# =============================================================================
# PROCESADOR DE HORARIOS
# =============================================================================
class ProcesadorHorarios:
    
    DIAS = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES']
    
    def __init__(self, start_row: int = 1):
        """
        Inicializador.
        :param start_row: Fila donde comienza la tabla de horario (0-indexed). 
                          Asumimos que las filas 0 y 1 contienen TÍTULO, TUTOR, CURSO/PARALELO.
        """
        self.cleaner = DataCleaner()
        self.start_row = start_row # Fila donde inician los números de clase (1, 2, 3...)
        self.columnas_horario = ['No', 'HORA'] + self.DIAS
    
    def _extraer_metadatos(self, df_raw: pd.DataFrame) -> Dict[str, str]:
        """Extrae el Curso, Paralelo y Docente Tutor del encabezado."""
        metadatos = {
            'curso': 'ND',
            'paralelo': 'ND',
            'docente_tutor': 'ND'
        }
        
        # 1. Extraer CURSO/PARALELO (Fila 0)
        # Buscar "PRIMERO A" en la segunda fila del Excel (índice 1 en pandas)
        # Asumimos que es la celda fusionada grande del título
        try:
            titulo = self.cleaner.normalizar_texto(df_raw.iloc[0, 3], titulo=False) # Suponemos celda fusionada en 0,3
            match = re.search(r'([A-Z]+)\s+([A-Z])$', titulo)
            if match:
                metadatos['curso'] = self.cleaner.normalizar_texto(match.group(1), titulo=True)
                metadatos['paralelo'] = match.group(2)
            else:
                # Si el título es solo "PRIMERO A", se ajusta
                partes = titulo.split()
                if len(partes) >= 2 and len(partes[-1]) == 1:
                    metadatos['curso'] = self.cleaner.normalizar_texto(" ".join(partes[:-1]), titulo=True)
                    metadatos['paralelo'] = partes[-1]
        except Exception as e:
            logger.warning(f"No se pudo extraer el curso/paralelo del encabezado. Error: {e}")

        # 2. Extraer DOCENTE TUTOR (Fila 1)
        # Buscar 'Lic.' en la segunda fila, debajo de CURSO/PARALELO
        try:
            tutor_raw = self.cleaner.normalizar_texto(df_raw.iloc[1, 3], titulo=False) # Suponemos celda debajo del título
            
            # Limpieza para quedarnos solo con el nombre
            tutor_nombre = re.sub(r'^(Lic\.?|Tg\.?)\s*', '', tutor_raw, flags=re.IGNORECASE)
            
            # Formatear el nombre
            metadatos['docente_tutor'] = self.cleaner.normalizar_texto(tutor_nombre, titulo=True)
        except Exception as e:
            logger.warning(f"No se pudo extraer el docente tutor del encabezado. Error: {e}")

        logger.info(f"Metadatos extraídos: {metadatos}")
        return metadatos

    def _descomponer_contenido_celda(self, contenido: str) -> Dict[str, str]:
        """
        Descompone el texto de la celda de la clase (e.g., 'Coro Lic. Daniel Laura. Sala 1 Bloque 1')
        en Asignatura, Docente, Aula y Bloque.
        """
        
        resultado = {
            'asignatura': '',
            'docente_clase': '',
            'aula': '',
            'bloque': ''
        }
        
        if pd.isna(contenido) or contenido.strip() == '':
            return resultado
        
        texto = contenido.strip()
        
        # Patrones de extracción
        # 1. Extraer AULA y BLOQUE (siempre al final)
        # Patrón: "Sala X Bloque Y" o "sala X bloque Y"
        match_aula_bloque = re.search(r'(sala|salón)\s*(\d+)\s*(bloque)?\s*(\d)?', texto, flags=re.IGNORECASE)
        if match_aula_bloque:
            try:
                # Obtener la parte que coincide con el aula/bloque
                aula_bloque_str = match_aula_bloque.group(0)
                
                # Extraer Sala/Aula
                match_sala = re.search(r'(sala|salón)\s*(\d+)', aula_bloque_str, flags=re.IGNORECASE)
                if match_sala:
                    resultado['aula'] = f"Sala {match_sala.group(2)}"
                    
                # Extraer Bloque
                match_bloque = re.search(r'bloque\s*(\d+)', aula_bloque_str, flags=re.IGNORECASE)
                if match_bloque:
                    resultado['bloque'] = f"Bloque {match_bloque.group(1)}"
                
                # Remover la parte extraída del texto original
                texto = texto.replace(aula_bloque_str, '').strip()
            except Exception as e:
                logger.warning(f"Error extrayendo aula/bloque: {e} en texto: {contenido}")


        # 2. Extraer DOCENTE y ASIGNATURA
        # El docente suele estar precedido por Lic. o Tg.
        
        # Patrón más específico: <Asignatura> (Lic. o Tg.) <Nombre Completo> .
        match_docente = re.search(
            r'(lic\.?|tg\.?)\s*([A-Za-zñÑáéíóúÁÉÍÓÚ\s]+)\.', 
            texto, flags=re.IGNORECASE
        )
        
        if match_docente:
            # Si se encuentra el patrón de docente
            try:
                docente_raw = match_docente.group(0)
                resultado['docente_clase'] = self.cleaner.normalizar_texto(
                    re.sub(r'^(Lic\.?|Tg\.?)\s*', '', docente_raw.strip('.').strip(), flags=re.IGNORECASE),
                    titulo=True
                )
                
                # La asignatura es lo que queda ANTES del patrón del docente
                asignatura_raw = texto.split(docente_raw)[0].strip()
                resultado['asignatura'] = self.cleaner.normalizar_texto(asignatura_raw, titulo=True)
                
            except Exception as e:
                logger.warning(f"Error extrayendo docente/asignatura con patrón: {e} en texto: {contenido}")

        else:
            # Si no hay un patrón claro, todo el texto es la asignatura
            resultado['asignatura'] = self.cleaner.normalizar_texto(texto, titulo=True)
            resultado['docente_clase'] = 'ND'


        # Caso especial: Si solo queda el nombre del docente (a veces el punto falla)
        if resultado['asignatura'] == '' and resultado['docente_clase'] != 'ND':
             resultado['asignatura'] = 'Clase sin Asignatura Específica'


        # Limpieza final
        resultado['asignatura'] = resultado['asignatura'].strip()
        resultado['docente_clase'] = resultado['docente_clase'].strip()
        
        return resultado

    def _descomponer_horas(self, hora_rango: str) -> Tuple[str, str]:
        """Descompone el rango 'HH:MM a HH:MM' en hora inicio y hora fin."""
        if pd.isna(hora_rango):
            return '', ''
        
        match = re.match(r'(\d{2}:\d{2})\s*a\s*(\d{2}:\d{2})', str(hora_rango).strip(), flags=re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
        return '', ''

    def procesar(self, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        """Función principal para procesar el archivo Excel."""
        
        logger.info(f"\nProcesando horario: {ruta_archivo} - Hoja '{sheet_name}'")
        
        try:
            # Leer el archivo sin encabezados para preservar la estructura de la tabla
            df_raw = pd.read_excel(ruta_archivo, sheet_name=sheet_name, header=None, engine='openpyxl')
            
            # 1. Extraer metadatos del Curso/Tutor
            metadatos = self._extraer_metadatos(df_raw)
            
            # 2. Identificar el área de la tabla de horario
            # Asumimos que la fila de encabezados de DÍAS (LUNES, MARTES...) está en self.start_row
            
            # Obtener los nombres de las columnas de la tabla de horarios
            # La tabla real empieza en la fila 3 (índice 2) según la imagen, pero ajustamos dinámicamente.
            df_clases = df_raw.iloc[self.start_row:].copy()
            
            # 3. Asignar nombres de columnas
            # Asumimos que las 7 primeras columnas son ['No', 'HORA', 'LUNES', ..., 'VIERNES']
            if df_clases.shape[1] >= len(self.columnas_horario):
                df_clases = df_clases.iloc[:, :len(self.columnas_horario)]
                df_clases.columns = self.columnas_horario
            else:
                logger.error("❌ El DataFrame de clases no tiene suficientes columnas para los días y horas.")
                return None

            # 4. Descomponer las celdas y aplanar el DataFrame
            registros = []
            
            for index, row in df_clases.iterrows():
                hora_rango = row['HORA']
                if pd.isna(hora_rango): continue # Saltar filas sin hora

                hora_inicio, hora_fin = self._descomponer_horas(hora_rango)
                
                for dia in self.DIAS:
                    contenido_celda = row[dia]
                    
                    if pd.isna(contenido_celda) or contenido_celda.strip() == '':
                        continue
                    
                    detalle_clase = self._descomponer_contenido_celda(contenido_celda)
                    
                    # Si el contenido está duplicado, significa que la clase dura dos o más horas (celda fusionada). 
                    # Procesamos solo el primero si la celda no es NaN.
                    # Asumimos que la lógica de Excel al leer celdas fusionadas llena la primera y deja NaN en las siguientes.
                    # Aquí la lógica es por fila, no por celda fusionada. Dejamos que pandas maneje la lectura.

                    registros.append({
                        'curso': metadatos['curso'],
                        'paralelo': metadatos['paralelo'],
                        'docente_tutor': metadatos['docente_tutor'],
                        'dia': dia,
                        'hora_inicio': hora_inicio,
                        'hora_fin': hora_fin,
                        'asignatura': detalle_clase['asignatura'],
                        'docente_clase': detalle_clase['docente_clase'],
                        'aula': detalle_clase['aula'],
                        'bloque': detalle_clase['bloque'],
                        'source_sheet': sheet_name
                    })

            df_final = pd.DataFrame(registros)
            
            logger.info(f"✅ Extraídos {len(df_final)} registros de asignación horaria")
            return df_final.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"❌ Error crítico procesando la hoja {sheet_name}: {e}", exc_info=True)
            return None

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main_horarios():
    print("\n" + "="*80)
    print("⏰ ETL - EXTRACCIÓN Y CONSOLIDACIÓN DE HORARIOS Y ASIGNACIONES")
    print("="*80)
    
    proc = ProcesadorHorarios(start_row=2) # start_row=2 asume que la fila 3 (index 2) es la primera fila de datos (07:30 a 08:15)
    datos_horarios = []
    
    # === 1. SOLICITAR RUTA Y ARCHIVO ===
    ruta_trabajo = input("Ingrese la ruta de la carpeta con archivos Excel de Horarios: ").strip()
    if not Path(ruta_trabajo).is_dir():
        logger.error(f"❌ La ruta '{ruta_trabajo}' no existe o no es un directorio.")
        return
    
    archivos_excel = [f for f in Path(ruta_trabajo).iterdir() if f.suffix in ['.xlsx', '.xls']]
    
    if not archivos_excel:
        logger.error("❌ No se encontraron archivos Excel de Horarios.")
        return
        
    print(f"\n📚 Archivos Excel encontrados ({len(archivos_excel)}):")
    for i, archivo in enumerate(archivos_excel, 1):
        print(f"  [{i}] {archivo.name}")
        
    seleccion = input("\nIngrese el número del archivo de Horario a procesar (ej: 1): ").strip()
    try:
        archivo_seleccionado = archivos_excel[int(seleccion) - 1]
    except:
        logger.error("❌ Selección inválida.")
        return
        
    # === 2. PROCESAR HOJAS ===
    logger.info(f"\n📄 Procesando archivo: {archivo_seleccionado.name}")
    try:
        xls = pd.ExcelFile(archivo_seleccionado, engine='openpyxl')
        for sheet_name in xls.sheet_names:
            df_temp = proc.procesar(str(archivo_seleccionado), sheet_name)
            if df_temp is not None:
                datos_horarios.append(df_temp)
    except Exception as e:
        logger.error(f"❌ Error leyendo o procesando el archivo {archivo_seleccionado.name}: {e}", exc_info=True)

    if not datos_horarios:
        logger.error("❌ No se pudo extraer información de Horarios.")
        return

    # === 3. CONSOLIDAR Y EXPORTAR ===
    df_final = pd.concat(datos_horarios, ignore_index=True)
    
    ruta_salida_referencias = './output_horarios'
    ruta_salida_final = Path(ruta_salida_referencias)
    ruta_salida_final.mkdir(exist_ok=True)
    
    nombre_archivo_salida = "HORARIOS_ASIGNACIONES_CONSOLIDADO.csv"
    
    df_final.to_csv(ruta_salida_final / nombre_archivo_salida, 
                    index=False, 
                    encoding='utf-8-sig', 
                    sep=';')
    
    logger.info(f"\n✅ EXPORTACIÓN CONSOLIDADA EXITOSA:")
    logger.info(f"   Ruta: {ruta_salida_final.resolve() / nombre_archivo_salida}")
    logger.info(f"   Total Registros: {len(df_final)}")
    print("\n" + "="*80)

if __name__ == "__main__":
    main_horarios()