# -*- coding: utf-8 -*- 
import pandas as pd
import os
import re
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import unicodedata

# =============================================================================
# CONFIGURACIÓN Y UTILIDADES COMUNES
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'etl_instrumento_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    SEPARADOR_CSV = ';'
    CODIFICACION_CSV = 'utf-8-sig'
    HOJAS_OMITIR = ['total', 'resumen', 'consolidado']
    
    # ⚠️ LISTAS DE CONTROL DE HOJAS
    HOJAS_INSTRUMENTO = ['vientos', 'guitarras', 'frotadas', 'teclados', 'percusion', 'cuerda', 'piano', 'saxofon', 'trompeta', 'violin', 'cello']
    HOJAS_AGRUPACIONES_EXCLUIR = ['acompañamiento', 'complementario', 'agrupaciones', 'conj inst', 'conjunto inst', 'coro']

    # Mapeo basado EXCLUSIVAMENTE en los 7 encabezados proporcionados
    MAPEO_COLUMNAS = {
        'no': 'id_temporal',
        'año_de_estudio': 'grado',
        'paralelo_señalar_el_mismo_paralelo_en_el_que_estuvieron_el_año_anterior': 'paralelo',
        'apellidos_del_estudiante': 'apellidos',
        'nombres_del_estudiante': 'nombres',
        'instrumento_que_estudia_en_el_conservatorio_bolívar': 'specialization_instrument',
        'maestro_de_instrumento': 'docente_nombre',
    }
    
    COLUMNAS_SALIDA = [
        'full_name', 'docente_nombre', 'specialization_instrument', 
        'grado', 'paralelo', 'tipo_asignacion', 
        'email_estudiante', 'docente_email' # Incluidos como FALTANTE
    ]

class DataCleaner:
    @staticmethod
    def normalizar_nombre_columna(nombre: str) -> str:
        if pd.isna(nombre): return 'sin_nombre'
        nombre = str(nombre).lower().strip()
        nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
        nombre = re.sub(r'[^\w\s]', '', nombre)
        return re.sub(r'\s+', '_', nombre).strip('_')

    @staticmethod
    def normalizar_texto(texto: str, titulo: bool = False) -> str:
        if pd.isna(texto) or texto == '': return ''
        texto = str(texto).strip()
        texto = re.sub(r'\s+', ' ', texto)
        if titulo: texto = texto.title()
        return texto

# =============================================================================
# PROCESADOR DE ASIGNACIONES DE INSTRUMENTO
# =============================================================================
class ProcesadorAsignaciones:
    def __init__(self):
        self.cleaner = DataCleaner()
    
    def procesar(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        sheet_name_lower = sheet_name.lower().strip()
        
        # 1. LÓGICA CONDICIONAL: Solo procesar hojas de instrumento
        if sheet_name_lower in Config.HOJAS_OMITIR: return None

        # Si el nombre de la hoja se parece a una agrupación, saltar
        if any(g in sheet_name_lower for g in Config.HOJAS_AGRUPACIONES_EXCLUIR):
            logger.info(f"⏭️ Saltando hoja '{sheet_name}': Es una Agrupación/General.")
            return None
        
        # Si el nombre de la hoja no contiene una palabra clave de instrumento, saltar
        if not any(i in sheet_name_lower for i in Config.HOJAS_INSTRUMENTO):
            logger.info(f"⏭️ Saltando hoja '{sheet_name}': No se identifica como Instrumento principal.")
            return None

        logger.info(f"✅ Extrayendo asignaciones: {archivo_nombre} - Hoja '{sheet_name}'")
        
        try:
            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, engine='openpyxl')
            
            # Normalizar y mapear encabezados
            df.columns = [self.cleaner.normalizar_nombre_columna(col) for col in df.columns]
            df = df.rename(columns={
                self.cleaner.normalizar_nombre_columna(k): v 
                for k, v in Config.MAPEO_COLUMNAS.items()
            })
            
            # 2. ELIMINAR ENCABEZADOS REPETIDOS
            # (Lógica omitida por simplicidad, confiando en que el mapeo basta)
            df = df.dropna(how='all', subset=['apellidos', 'nombres']).copy()
            
            # 3. VERIFICACIÓN Y LIMPIEZA DE COLUMNAS CLAVE
            df['apellidos'] = df.get('apellidos', pd.Series()).apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            df['nombres'] = df.get('nombres', pd.Series()).apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            df['full_name'] = df['apellidos'] + ' ' + df['nombres']
            df = df[df['full_name'].str.strip() != '']
            
            df['specialization_instrument'] = df.get('specialization_instrument', pd.Series('NULO')).apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            df['docente_nombre'] = df.get('docente_nombre', pd.Series('NULO')).apply(self.cleaner.normalizar_texto, titulo=True)
            
            df['grado'] = df.get('grado', pd.Series('ND')).astype(str).str.strip()
            df['paralelo'] = df.get('paralelo', pd.Series('A')).astype(str).str.strip()
            
            # 4. COLUMNAS CON VALOR FIJO (Emails)
            df['email_estudiante'] = 'FALTANTE'
            df['docente_email'] = 'FALTANTE'
            df['tipo_asignacion'] = self.cleaner.normalizar_texto(sheet_name, titulo=True)

            # 5. EXPORTAR Y LIMPIAR
            df_export = df[[c for c in Config.COLUMNAS_SALIDA if c in df.columns]].copy()
            
            logger.info(f"✅ Extraídas {len(df_export)} asignaciones de Instrumento de '{sheet_name}'")
            return df_export
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo asignaciones de {sheet_name}: {e}", exc_info=True)
            return None

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main_instrumento():
    print("\n" + "="*70)
    print("🎼 ETL - EXTRACCIÓN Y CONSOLIDACIÓN DE INSTRUMENTO")
    print("="*70)
    
    proc_asignaciones = ProcesadorAsignaciones()
    datos_asignaciones = []
    
    ruta_trabajo = input("Ingrese la ruta de la carpeta con archivos Excel (Distribucion): ").strip()
    if not os.path.exists(ruta_trabajo):
        logger.error(f"❌ La ruta '{ruta_trabajo}' no existe")
        return
    
    archivos_excel = [f for f in os.listdir(ruta_trabajo) if f.endswith(('.xlsx', '.xls'))]
    
    for archivo in archivos_excel:
        if 'Distribucion' in archivo or 'distribucion' in archivo:
            ruta_completa = os.path.join(ruta_trabajo, archivo)
            try:
                xls = pd.ExcelFile(ruta_completa, engine='openpyxl')
                for sheet_name in xls.sheet_names:
                    df_temp = proc_asignaciones.procesar(archivo, ruta_completa, sheet_name)
                    if df_temp is not None:
                        datos_asignaciones.append(df_temp)
            except Exception as e:
                logger.error(f"❌ Error procesando archivo {archivo}: {str(e)}", exc_info=True)

    if not datos_asignaciones:
        logger.error("❌ No se pudo extraer ninguna asignación de Instrumento")
        return

    df_final = pd.concat(datos_asignaciones, ignore_index=True)
    
    # EXPORTACIÓN CONSOLIDADA
    ruta_salida_referencias = './output'
    ruta_salida_final = Path(ruta_salida_referencias)
    ruta_salida_final.mkdir(exist_ok=True)
    
    df_final.to_csv(ruta_salida_final / "INSTRUMENTO_ASIGNACIONES_CONSOLIDADO.csv", 
                    index=False, encoding=Config.CODIFICACION_CSV, sep=Config.SEPARADOR_CSV)
    logger.info(f"\n✅ EXPORTACIÓN CONSOLIDADA EXITOSA: {ruta_salida_final / 'INSTRUMENTO_ASIGNACIONES_CONSOLIDADO.csv'} ({len(df_final)} asignaciones)")

    # EXPORTACIÓN POR ÁREA INSTRUMENTAL
    ruta_salida_area = ruta_salida_final / "asignaciones_instrumento"
    ruta_salida_area.mkdir(exist_ok=True)
    
    df_final_clean = df_final.dropna(subset=['specialization_instrument'])
    instrumentos_grupos = df_final_clean.groupby('specialization_instrument')
    
    logger.info(f"\n👉 Exportando por área instrumental en: {ruta_salida_area.resolve()}")
    
    for instrumento, grupo_df in instrumentos_grupos:
        nombre_archivo = re.sub(r'[^\w\-_\.]', '_', instrumento.lower())
        ruta_csv = ruta_salida_area / f"ASIGNACIONES_{nombre_archivo}.csv"
        
        grupo_df.to_csv(ruta_csv, index=False, encoding=Config.CODIFICACION_CSV, sep=Config.SEPARADOR_CSV)
        logger.info(f"  [OK] Exportadas {len(grupo_df)} asignaciones para '{instrumento}'")

if __name__ == "__main__":
    main_instrumento()