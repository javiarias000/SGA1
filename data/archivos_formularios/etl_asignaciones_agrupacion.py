import pandas as pd
import os
import re
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path
import unicodedata

# =============================================================================
# CONFIGURACIÓN Y UTILIDADES COMUNES
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'etl_process_agrupaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    CODIFICACION_JSON = 'utf-8'
    HOJAS_OMITIR = ['total', 'resumen', 'consolidado']
    
    # Mapeo de columnas mejorado
    MAPEO_COLUMNAS = {
        # Identificadores
        'no': 'numero',
        'n': 'numero',
        # Año y Paralelo
        'ano_de_paralelo': 'ano_paralelo',
        'ano_de_paralelo_sesion': 'ano_paralelo',
        'paralelo_sesion': 'paralelo_info',
        'paralelo': 'paralelo',
        # Datos del Estudiante
        'apellidos_del_estudiante': 'apellidos',
        'nombres_del_estudiante': 'nombres',
        'nombres_del_est': 'nombres',
        # Instrumentos
        'instrumento_que_estudia_en_el_conservatorio_bolivar': 'instrumento',
        'instrumento_que_estudia': 'instrumento',
        'instrumento_que_estuda': 'instrumento',
        'instrumento_que_estud': 'instrumento',
        # Agrupación
        'agrupacion': 'agrupacion',
    }

class DataCleaner:
    @staticmethod
    def normalizar_nombre_columna(nombre: str) -> str:
        """Normaliza nombres de columnas para comparación"""
        if pd.isna(nombre) or str(nombre).strip() == '':
            return 'sin_nombre'
        nombre = str(nombre).lower().strip()
        # Remover acentos
        nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
        # Remover caracteres especiales excepto guiones bajos
        nombre = re.sub(r'[^\w\s]', '', nombre)
        # Reemplazar espacios con guiones bajos
        nombre = re.sub(r'\s+', '_', nombre)
        return nombre.strip('_')

    @staticmethod
    def normalizar_texto(texto: str, titulo: bool = False) -> str:
        """Limpia y normaliza texto"""
        if pd.isna(texto) or str(texto).strip() == '':
            return ''
        texto = str(texto).strip()
        texto = re.sub(r'\s+', ' ', texto)
        if titulo:
            texto = texto.title()
        return texto
    
    @staticmethod
    def extraer_ano_paralelo(texto: str) -> Dict[str, str]:
        """Extrae año y paralelo de texto combinado como '10o (2o B (vespertina))'"""
        if pd.isna(texto):
            return {'ano': '', 'paralelo': '', 'sesion': ''}
        
        texto = str(texto).strip()
        ano = ''
        paralelo = ''
        sesion = ''
        
        # Buscar año (número seguido de 'o' o 'O')
        match_ano = re.search(r'(\d+)[oO]', texto)
        if match_ano:
            ano = match_ano.group(1)
        
        # Buscar paralelo (letra mayúscula)
        match_paralelo = re.search(r'\b([A-Z])\b', texto)
        if match_paralelo:
            paralelo = match_paralelo.group(1)
        
        # Buscar sesión (vespertina, matutina, etc.)
        if 'vespertina' in texto.lower():
            sesion = 'Vespertina'
        elif 'matutina' in texto.lower():
            sesion = 'Matutina'
        
        return {
            'ano': ano,
            'paralelo': paralelo,
            'sesion': sesion
        }

# =============================================================================
# PROCESADOR ESPECÍFICO DE ASIGNACIONES
# =============================================================================
class ProcesadorAsignaciones:
    def __init__(self):
        self.cleaner = DataCleaner()
    
    def detectar_fila_encabezados(self, df: pd.DataFrame) -> int:
        """Detecta la fila que contiene los encabezados reales"""
        for idx in range(min(10, len(df))):
            fila = df.iloc[idx]
            # Buscar palabras clave de encabezados
            texto_fila = ' '.join([str(val).lower() for val in fila if pd.notna(val)])
            if any(keyword in texto_fila for keyword in ['apellidos', 'nombres', 'estudiante', 'agrupacion']):
                return idx
        return 0
    
    def procesar_hoja(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[List[Dict]]:
        """Procesa una hoja del Excel y retorna lista de diccionarios"""
        logger.info(f"Procesando: {archivo_nombre} - Hoja '{sheet_name}'")
        
        try:
            # Leer sin encabezados primero
            df_raw = pd.read_excel(ruta_archivo, sheet_name=sheet_name, header=None, engine='openpyxl')
            
            # Detectar fila de encabezados
            header_row = self.detectar_fila_encabezados(df_raw)
            
            # Leer con encabezados correctos
            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, header=header_row, engine='openpyxl')
            
            # Normalizar nombres de columnas
            columnas_normalizadas = []
            columnas_vistas = {}
            
            for col in df.columns:
                col_normalizada = self.cleaner.normalizar_nombre_columna(col)
                
                # Manejar columnas duplicadas
                if col_normalizada in columnas_vistas:
                    columnas_vistas[col_normalizada] += 1
                    col_normalizada = f"{col_normalizada}_{columnas_vistas[col_normalizada]}"
                else:
                    columnas_vistas[col_normalizada] = 0
                
                columnas_normalizadas.append(col_normalizada)
            
            df.columns = columnas_normalizadas
            
            # Aplicar mapeo de columnas
            mapeo_aplicado = {}
            for col_original, col_nueva in Config.MAPEO_COLUMNAS.items():
                col_norm = self.cleaner.normalizar_nombre_columna(col_original)
                if col_norm in df.columns:
                    mapeo_aplicado[col_norm] = col_nueva
            
            df = df.rename(columns=mapeo_aplicado)
            
            # Eliminar filas completamente vacías
            df = df.dropna(how='all')
            
            # Procesar cada fila
            registros = []
            for idx, row in df.iterrows():
                registro = {}
                
                # Extraer campos básicos
                for col in df.columns:
                    valor = row[col]
                    if pd.notna(valor) and str(valor).strip() != '':
                        registro[col] = self.cleaner.normalizar_texto(str(valor))
                
                # Construir nombre completo
                if 'apellidos' in registro and 'nombres' in registro:
                    registro['nombre_completo'] = self.cleaner.normalizar_texto(
                        f"{registro['apellidos']} {registro['nombres']}", 
                        titulo=True
                    )
                
                # Procesar año y paralelo si existe la columna combinada
                if 'ano_paralelo' in registro:
                    info_curso = self.cleaner.extraer_ano_paralelo(registro['ano_paralelo'])
                    registro['curso'] = info_curso['ano']
                    if not registro.get('paralelo'):
                        registro['paralelo'] = info_curso['paralelo']
                    if info_curso['sesion']:
                        registro['sesion'] = info_curso['sesion']
                
                # Agregar metadatos
                registro['archivo_origen'] = archivo_nombre
                registro['hoja_origen'] = sheet_name
                
                # Solo agregar si tiene nombre completo o apellidos
                if registro.get('nombre_completo') or registro.get('apellidos'):
                    registros.append(registro)
            
            logger.info(f"✅ Extraídos {len(registros)} registros de '{sheet_name}'")
            return registros
            
        except Exception as e:
            logger.error(f"❌ Error procesando {sheet_name}: {str(e)}", exc_info=True)
            return None

# =============================================================================
# CONSOLIDADOR Y EXPORTADOR PRINCIPAL
# =============================================================================
def main_agrupaciones():
    print("\n" + "="*70)
    print("🎵 ETL - EXTRACCIÓN Y CONSOLIDACIÓN DE AGRUPACIONES (JSON)")
    print("="*70)
    
    ruta_trabajo = input("\nIngrese la ruta de la carpeta con archivos Excel: ").strip()
    if not ruta_trabajo:
        ruta_trabajo = './'
        print("Usando la carpeta actual (./)")
    
    if not os.path.exists(ruta_trabajo):
        logger.error(f"❌ La ruta '{ruta_trabajo}' no existe")
        return
    
    archivos_excel = [f for f in os.listdir(ruta_trabajo) 
                     if f.endswith(('.xlsx', '.xls')) and not f.startswith('~$')]
    
    if not archivos_excel:
        logger.error("❌ No se encontraron archivos Excel en la ruta especificada")
        return
    
    logger.info(f"📁 Archivos encontrados: {len(archivos_excel)}")
    
    procesador = ProcesadorAsignaciones()
    todos_registros = []
    
    # Procesar cada archivo
    for archivo in archivos_excel:
        logger.info(f"\n📄 Procesando archivo: {archivo}")
        ruta_completa = os.path.join(ruta_trabajo, archivo)
        
        try:
            xls = pd.ExcelFile(ruta_completa, engine='openpyxl')
            
            for sheet_name in xls.sheet_names:
                if sheet_name.lower() not in Config.HOJAS_OMITIR:
                    registros = procesador.procesar_hoja(archivo, ruta_completa, sheet_name)
                    if registros:
                        todos_registros.extend(registros)
                        
        except Exception as e:
            logger.error(f"❌ Error procesando archivo {archivo}: {str(e)}", exc_info=True)
    
    # Exportar resultados
    if todos_registros:
        # Crear carpeta de salida
        ruta_salida = Path('./output')
        ruta_salida.mkdir(exist_ok=True)
        
        # Exportar JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_json = ruta_salida / f"AGRUPACION_ASIGNACIONES_{timestamp}.json"
        
        with open(ruta_json, 'w', encoding=Config.CODIFICACION_JSON) as f:
            json.dump(todos_registros, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ EXPORTACIÓN EXITOSA")
        logger.info(f"📊 Total de registros: {len(todos_registros)}")
        logger.info(f"💾 Archivo: {ruta_json}")
        
        # Mostrar resumen de campos
        campos_unicos = set()
        for registro in todos_registros:
            campos_unicos.update(registro.keys())
        
        logger.info(f"\n📋 Campos extraídos ({len(campos_unicos)}):")
        for campo in sorted(campos_unicos):
            logger.info(f"   - {campo}")
        
        # Opcionalmente, también exportar CSV para verificación
        df_export = pd.DataFrame(todos_registros)
        ruta_csv = ruta_salida / f"AGRUPACION_ASIGNACIONES_{timestamp}.csv"
        df_export.to_csv(ruta_csv, index=False, encoding='utf-8-sig', sep=';')
        logger.info(f"💾 También exportado como CSV: {ruta_csv}")
        
    else:
        logger.error("❌ No se pudo extraer ningún registro")

if __name__ == "__main__":
    main_agrupaciones()