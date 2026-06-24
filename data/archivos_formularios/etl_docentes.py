import pandas as pd
import os
import re
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import unicodedata

# =============================================================================
# CONFIGURACIÓN Y UTILIDADES COMUNES
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'etl_process_docentes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    SEPARADOR_CSV = ';'
    CODIFICACION_CSV = 'utf-8-sig'
    DOMINIO_DOCENTE = 'conservatoriobolivar.edu.ec'
    PASSWORD_DEFAULT = 'Cb2025$'
    HOJAS_OMITIR = ['total', 'resumen', 'consolidado']
    
    MAPEO_COLUMNAS = {
        'maestro_de_instrumento': 'teacher_name_instrumento',
        'docente_piano_acompanamiento': 'teacher_name_acompanamiento',
        'docente_piano_complementario': 'teacher_name_complementario',
        'docente': 'teacher_name', 
        'profesor': 'teacher_name',
        'apellidos_y_nombres': 'full_name', # Nuevo mapeo
    }

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

    @staticmethod
    def generar_username_desde_nombre(nombre_completo: str, dominio: str = None) -> str:
        if pd.isna(nombre_completo) or nombre_completo == '': return ''
        username = nombre_completo.lower().strip()
        username = unicodedata.normalize('NFKD', username).encode('ASCII', 'ignore').decode('utf-8')
        username = re.sub(r'[^a-z\s]', '', username)
        username = re.sub(r'\s+', '.', username).strip('.')
        if dominio: return f"{username}@{dominio}"
        return username

# =============================================================================
# PROCESADOR ESPECÍFICO DE DOCENTES
# =============================================================================
class ProcesadorDocentes:
    def __init__(self):
        self.cleaner = DataCleaner()
    
    def procesar(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        logger.info(f"Extrayendo docentes: {archivo_nombre} - Hoja '{sheet_name}'")

        try:
            header_row = None
            if "DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx" in archivo_nombre:
                header_row = 2

            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, engine='openpyxl', header=header_row)
            df.columns = [self.cleaner.normalizar_nombre_columna(col) for col in df.columns]

            df = df.rename(columns={
                self.cleaner.normalizar_nombre_columna(k): v
                for k, v in Config.MAPEO_COLUMNAS.items()
            })

            if "DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx" in archivo_nombre:
                if 'full_name' not in df.columns or 'correo_electronico_institucional' not in df.columns:
                    logger.error(f"Las columnas 'full_name' o 'correo_electronico_institucional' no se encontraron en {archivo_nombre}")
                    return None

                df_docentes = df[['full_name', 'correo_electronico_institucional']].copy()
                df_docentes.rename(columns={'correo_electronico_institucional': 'email'}, inplace=True)

                df_docentes['full_name'] = df_docentes['full_name'].apply(
                    lambda x: self.cleaner.normalizar_texto(x, titulo=True)
                )

                # Handle missing emails - if email is missing, generate it from the name as a fallback
                df_docentes['email'] = df_docentes.apply(
                    lambda row: self.cleaner.normalizar_texto(row['email']) if pd.notna(row['email']) and row['email'] != '' else self.cleaner.generar_username_desde_nombre(row['full_name'], Config.DOMINIO_DOCENTE),
                    axis=1
                )

            else: # Logic for other file types
                cols_docentes = [
                    'teacher_name_instrumento', 'teacher_name_acompanamiento',
                    'teacher_name_complementario', 'teacher_name'
                ]
                nombres_docentes = []
                for col in cols_docentes:
                    if col in df.columns:
                        nombres_docentes.extend(df[col].dropna().astype(str).tolist())

                if not nombres_docentes:
                    return None

                df_docentes = pd.DataFrame({'full_name': nombres_docentes})
                df_docentes['full_name'] = df_docentes['full_name'].apply(
                    lambda x: self.cleaner.normalizar_texto(x, titulo=True)
                )
                df_docentes['email'] = df_docentes['full_name'].apply(
                    lambda x: self.cleaner.generar_username_desde_nombre(x, Config.DOMINIO_DOCENTE)
                )


            df_docentes = df_docentes[df_docentes['full_name'].str.strip() != '']
            df_docentes = df_docentes[df_docentes['full_name'] != 'Nan']
            df_docentes = df_docentes.drop_duplicates(subset=['email'], keep='first')

            df_docentes['rol'] = 'DOCENTE'
            df_docentes['username'] = df_docentes['email']
            df_docentes['password_plano'] = Config.PASSWORD_DEFAULT

            df_docentes = df_docentes[['full_name', 'email', 'username', 'password_plano', 'rol']]

            logger.info(f"✅ Extraídos {len(df_docentes)} docentes únicos de '{sheet_name}'")
            return df_docentes

        except Exception as e:
            logger.error(f"❌ Error extrayendo docentes de {sheet_name}: {str(e)}", exc_info=True)
            return None

# =============================================================================
# CONSOLIDADOR Y EXPORTADOR PRINCIPAL
# =============================================================================
def main_docentes():
    print("\n" + "="*70)
    print("👨‍🏫 ETL - EXTRACCIÓN Y CONSOLIDACIÓN DE DOCENTES ÚNICOS")
    print("="*70)
    
    # Ruta hardcodeada para el archivo específico
    ruta_archivo = "archivos_formularios/DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx"
    if not os.path.exists(ruta_archivo):
        logger.error(f"❌ La ruta '{ruta_archivo}' no existe")
        return
    
    proc_docentes = ProcesadorDocentes()
    datos_docentes = []
    
    # Procesar el archivo específico
    try:
        xls = pd.ExcelFile(ruta_archivo, engine='openpyxl')
        for sheet_name in xls.sheet_names:
            if sheet_name.lower() == 'general': # Solo procesar la hoja 'GENERAL'
                df_doc = proc_docentes.procesar("DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx", ruta_archivo, sheet_name)
                if df_doc is not None:
                    datos_docentes.append(df_doc)
            elif sheet_name.lower() == 'ies':
                logger.info(f"Ignorando hoja '{sheet_name}'")
    except Exception as e:
        logger.error(f"❌ Error procesando archivo {ruta_archivo}: {str(e)}", exc_info=True)
    
    if datos_docentes:
        df_docentes_final = pd.concat(datos_docentes, ignore_index=True)
        df_docentes_final = df_docentes_final.drop_duplicates(subset=['email'], keep='first')
        
        # Exportar
        ruta_salida = Path('./base_de_datos_json/personal_docente') # Cambiar ruta de salida
        ruta_salida.mkdir(exist_ok=True)
        ruta_archivo_csv = ruta_salida / "DOCENTES.csv"
        ruta_archivo_json = ruta_salida / "DOCENTES.json"
        
        df_docentes_final.to_csv(
            ruta_archivo_csv,
            index=False,
            encoding=Config.CODIFICACION_CSV,
            sep=Config.SEPARADOR_CSV
        )
        df_docentes_final.to_json(
            ruta_archivo_json,
            orient='records',
            lines=True,
            force_ascii=False
        )
        logger.info(f"\n✅ EXPORTACIÓN EXITOSA: {ruta_archivo_csv} y {ruta_archivo_json} ({len(df_docentes_final)} docentes)")
    else:
        logger.error("❌ No se pudo extraer ningún dato de docente")

if __name__ == "__main__":
    main_docentes()