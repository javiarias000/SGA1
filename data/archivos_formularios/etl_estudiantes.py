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
        logging.FileHandler(f'etl_process_estudiantes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    SEPARADOR_CSV = ';'
    CODIFICACION_CSV = 'utf-8-sig'
    DOMINIO_DOCENTE = 'conservatoriobolivar.edu.ec'
    PASSWORD_DEFAULT = 'Cb2025$'
    PATRON_EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PATRON_CEDULA_EC = r'^\d{10}$'
    PATRON_CELULAR_EC = r'^09\d{8}$'
    HOJAS_OMITIR = ['total', 'resumen', 'consolidado']
    
    # Mapeo de columnas ampliado para mayor robustez
    MAPEO_COLUMNAS = {
        # ESTUDIANTE - EMAIL
        'dirección_de_correo_electrónico': 'email_estudiante',
        'email_estudiante': 'email_estudiante',

        # ESTUDIANTE - APELLIDOS (NUEVAS VARIACIONES AGREGADAS)
        'apellidos_del_estudiante': 'apellidos',
        'apellidos_del_estudiante_escribir_la_primera_letra_en_mayúsculas_y_las demás_en_minúsculas_por_ejemplo_pérez_lópez': 'apellidos',
        'apellidos_estudiante': 'apellidos',
        'apellido': 'apellidos', 
        'apellidos': 'apellidos', 
        'ape': 'apellidos', # NUEVO
        'apell': 'apellidos', # NUEVO
        'apellido_del_estudiante': 'apellidos', # NUEVO
        'primer_apellido': 'apellidos', # NUEVO
        'apellidos_nombres': 'full_name', # Mapeo de columnas combinadas
        
        # ESTUDIANTE - NOMBRES (NUEVAS VARIACIONES AGREGADAS)
        'nombres_del_estudiante': 'nombres',
        'nombres_estudiante': 'nombres',
        'nombre': 'nombres', 
        'nombres': 'nombres', 
        'nom': 'nombres', # NUEVO
        'nomb': 'nombres', # NUEVO
        'nombre_del_estudiante': 'nombres', # NUEVO
        
        # GRADO Y PARALELO
        'año_de_estudio': 'grado',
        'curso': 'grado',
        'paralelo': 'paralelo',
        'par': 'paralelo', 
        'paralelo_de_curso': 'paralelo', # NUEVO
        'paralelo_asignado': 'paralelo', # NUEVO
        'seccion': 'paralelo', # NUEVO
        
        # OTROS ESTUDIANTE
        'no': 'id_temporal',
        'cedula': 'cedula',
        'cédula': 'cedula',
        'cedula_estudiante': 'cedula',
        'identificacion': 'cedula', # NUEVO
        
        # REPRESENTANTE
        'nombres_completos_del_representante': 'rep_nombres',
        'apellidos_completos_del_representante': 'rep_apellidos',
        'número_de_cédula_del_representante': 'rep_cedula',
        'cedula_del_representante': 'rep_cedula',
        'celular_del_representante_padre_o_madre': 'rep_celular',
        'celular_representante': 'rep_celular',
        'correo_electrónico_del_representante': 'rep_email',
        'email_representante': 'rep_email',
        'apellidos_representante': 'rep_apellidos', # NUEVO
        'nombres_representante': 'rep_nombres', # NUEVO
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
    def limpiar_email(email: str) -> str:
        if pd.isna(email): return ''
        return re.sub(r'\s+', '', str(email).lower().strip())
    
    @staticmethod
    def limpiar_cedula(cedula: str) -> str:
        if pd.isna(cedula): return ''
        return re.sub(r'\D', '', str(cedula))

    @staticmethod
    def limpiar_celular(celular: str) -> str:
        if pd.isna(celular): return ''
        celular = re.sub(r'\D', '', str(celular))
        if len(celular) == 9 and celular[0] == '9': celular = '0' + celular
        return celular

class DataValidator:
    @staticmethod
    def validar_email(email: str) -> bool:
        if pd.isna(email) or email == '': return False
        return bool(re.match(Config.PATRON_EMAIL, str(email)))
    
    @staticmethod
    def validar_cedula_ecuatoriana(cedula: str) -> bool:
        if pd.isna(cedula) or cedula == '': return False
        cedula = str(cedula).strip()
        if not re.match(Config.PATRON_CEDULA_EC, cedula): return False
        try:
            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            suma = 0
            for i in range(9):
                valor = int(cedula[i]) * coeficientes[i]
                suma += valor if valor < 10 else valor - 9
            digito_verificador = (10 - (suma % 10)) % 10
            return digito_verificador == int(cedula[9])
        except: return False
    
    @staticmethod
    def validar_celular_ecuatoriano(celular: str) -> bool:
        if pd.isna(celular) or celular == '': return False
        return bool(re.match(Config.PATRON_CELULAR_EC, str(celular)))

class DataQualityReport:
    def __init__(self): self.issues = []
    def add_issue(self, categoria: str, detalle: str, cantidad: int = 1):
        self.issues.append({'categoria': categoria, 'detalle': detalle, 'cantidad': cantidad})
    def generar_reporte(self) -> str:
        if not self.issues: return "✅ No se detectaron problemas de calidad"
        reporte = "\n📊 REPORTE DE CALIDAD DE DATOS:\n" + "=" * 60 + "\n"
        for issue in self.issues:
            reporte += f"  ⚠️  {issue['categoria']}: {issue['detalle']} ({issue['cantidad']})\n"
        return reporte

# =============================================================================
# PROCESADOR ESPECÍFICO DE ESTUDIANTES
# =============================================================================
class ProcesadorEstudiantes:
    def __init__(self):
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.quality_report = DataQualityReport()
    
    def procesar(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        logger.info(f"Procesando estudiantes: {archivo_nombre} - Hoja '{sheet_name}'")
        if sheet_name.lower() in Config.HOJAS_OMITIR: return None
        
        try:
            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, engine='openpyxl')
            df.columns = [self.cleaner.normalizar_nombre_columna(col) for col in df.columns]
            df = df.rename(columns={
                self.cleaner.normalizar_nombre_columna(k): v 
                for k, v in Config.MAPEO_COLUMNAS.items()
            })
            
            # --- Limpieza de Estudiante ---
            if 'email_estudiante' not in df.columns:
                logger.error(f"Columna 'email_estudiante' no encontrada en {sheet_name}")
                return None
            df['email'] = df['email_estudiante'].apply(self.cleaner.limpiar_email)
            df = df[df['email'].apply(self.validator.validar_email)]

            if 'apellidos' not in df.columns or 'nombres' not in df.columns:
                # ⚠️ FIX: Reportar las columnas disponibles para la depuración
                logger.error(f"Columnas 'apellidos' o 'nombres' no encontradas en {sheet_name}. Columnas disponibles (normalizadas): {list(df.columns)}")
                return None
            
            # Si 'apellidos_nombres' existe, intenta dividirlo. (caso de columna combinada)
            if 'apellidos_nombres' in df.columns and ('apellidos' not in df.columns or 'nombres' not in df.columns):
                try:
                    df[['apellidos', 'nombres']] = df['apellidos_nombres'].str.split(n=1, expand=True)
                except:
                    # No se pudo dividir, dejar como está y el full_name tomará el valor completo
                    pass
            
            df['apellidos'] = df['apellidos'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            df['nombres'] = df['nombres'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            df['full_name'] = df['apellidos'] + ' ' + df['nombres']
            df = df[df['full_name'].str.strip() != '']
            
            if 'cedula' in df.columns:
                df['cedula'] = df['cedula'].apply(self.cleaner.limpiar_cedula)
            
            if 'grado' not in df.columns:
                grado_match = re.search(r'(\d+)', sheet_name)
                df['grado'] = grado_match.group(1) if grado_match else 'ND'
            df['grado'] = df['grado'].astype(str).str.strip()
            
            # Asignación y limpieza robusta del paralelo
            if 'paralelo' in df.columns:
                # Limpiar y estandarizar el paralelo (ej. 1A -> A, A/B/C -> A, B, C)
                df['paralelo'] = df['paralelo'].astype(str).str.strip().str.upper().str.replace(r'[^A-Z]', '', regex=True)
                df.loc[df['paralelo'] == '', 'paralelo'] = 'A'
            else:
                df['paralelo'] = 'A' # Asignar un valor por defecto si la columna no existe

            # --- Limpieza de Representante ---
            if 'rep_nombres' in df.columns: df['rep_nombres'] = df['rep_nombres'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            if 'rep_apellidos' in df.columns: df['rep_apellidos'] = df['rep_apellidos'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            if 'rep_email' in df.columns: df['rep_email'] = df['rep_email'].apply(self.cleaner.limpiar_email)
            if 'rep_cedula' in df.columns: df['rep_cedula'] = df['rep_cedula'].apply(self.cleaner.limpiar_cedula)
            if 'rep_celular' in df.columns: df['rep_celular'] = df['rep_celular'].apply(self.cleaner.limpiar_celular)
            
            df['rol'] = 'ESTUDIANTE'
            df['username'] = df['email']
            df['password_plano'] = Config.PASSWORD_DEFAULT
            
            logger.info(f"✅ Procesados {len(df)} estudiantes de '{sheet_name}'")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error procesando {sheet_name}: {str(e)}", exc_info=True)
            return None

# =============================================================================
# CONSOLIDADOR Y EXPORTADOR PRINCIPAL
# =============================================================================
def main_estudiantes():
    print("\n" + "="*70)
    print("👨‍🎓 ETL - EXTRACCIÓN Y CONSOLIDACIÓN DE ESTUDIANTES/REPRESENTANTES")
    print("="*70)
    
    ruta_trabajo = input("Ingrese la ruta de la carpeta con archivos Excel (Matriculados): ").strip()
    if not os.path.exists(ruta_trabajo):
        logger.error(f"❌ La ruta '{ruta_trabajo}' no existe")
        return
    
    archivos_excel = [f for f in os.listdir(ruta_trabajo) if f.endswith(('.xlsx', '.xls'))]
    proc_estudiantes = ProcesadorEstudiantes()
    datos_estudiantes = []
    
    for archivo in archivos_excel:
        if 'Matriculados' in archivo or 'matriculados' in archivo:
            ruta_completa = os.path.join(ruta_trabajo, archivo)
            try:
                xls = pd.ExcelFile(ruta_completa, engine='openpyxl')
                for sheet_name in xls.sheet_names:
                    if sheet_name.lower() not in Config.HOJAS_OMITIR:
                        df_temp = proc_estudiantes.procesar(archivo, ruta_completa, sheet_name)
                        if df_temp is not None:
                            datos_estudiantes.append(df_temp)
            except Exception as e:
                logger.error(f"❌ Error procesando archivo {archivo}: {str(e)}", exc_info=True)
    
    if datos_estudiantes:
        # Concatenar todos los estudiantes sin deduplicar por email.
        df_est_final = pd.concat(datos_estudiantes, ignore_index=True)
        
        # 1. Generar archivo de Estudiantes
        cols_estudiante = ['full_name', 'email', 'username', 'password_plano', 'cedula', 'grado', 'paralelo', 'rol']
        cols_representante = ['rep_nombres', 'rep_apellidos', 'rep_cedula', 'rep_celular', 'rep_email']
        
        df_est_export = df_est_final.copy()
        df_est_export = df_est_export[[c for c in cols_estudiante + cols_representante if c in df_est_export.columns]]
        df_est_export = df_est_export.sort_values(['grado', 'paralelo', 'full_name']).reset_index(drop=True)
        
        # 2. Generar archivo de Representantes (Deduplicación por Cédula/Email del Representante)
        cols_rep = [c for c in df_est_final.columns if c.startswith('rep_')]
        df_rep = df_est_final[cols_rep].copy()

        if df_rep.empty:
             logger.warning("⚠️  No se encontraron datos válidos de representantes para exportar.")
             df_rep_export = pd.DataFrame()
        else:
            df_rep = df_rep.dropna(how='all')

            if df_rep.empty:
                logger.warning("⚠️  Los datos de representante encontrados estaban vacíos después de la limpieza.")
                df_rep_export = pd.DataFrame()
            else:
                df_rep['rep_id'] = df_rep.get('rep_cedula', pd.Series()).fillna(df_rep.get('rep_email', pd.Series()))
                df_rep = df_rep.dropna(subset=['rep_id']).drop_duplicates(subset=['rep_id'], keep='first').drop(columns=['rep_id'])
                
                cols_rep_orden = [c for c in cols_representante if c in df_rep.columns]
                df_rep_export = df_rep[cols_rep_orden]
                
                # Lógica de ordenamiento robusta
                sort_key = None
                if 'rep_apellidos' in df_rep_export.columns and not df_rep_export['rep_apellidos'].isnull().all():
                    sort_key = 'rep_apellidos'
                elif 'rep_nombres' in df_rep_export.columns and not df_rep_export['rep_nombres'].isnull().all():
                    sort_key = 'rep_nombres'
                
                if sort_key:
                    df_rep_export = df_rep_export.sort_values(sort_key).reset_index(drop=True)
                else:
                    logger.warning("⚠️ Faltan columnas de nombre ('rep_apellidos' y 'rep_nombres') en el archivo de representantes. No se aplicará ordenamiento alfabético.")
                    df_rep_export = df_rep_export.reset_index(drop=True)
        
        # Exportar
        ruta_salida = Path('./output')
        ruta_salida.mkdir(exist_ok=True)
        
        df_est_export.to_csv(ruta_salida / "ESTUDIANTES_CON_REPRESENTANTES.csv", index=False, encoding=Config.CODIFICACION_CSV, sep=Config.SEPARADOR_CSV)
        logger.info(f"\n✅ EXPORTACIÓN EXITOSA: {ruta_salida / 'ESTUDIANTES_CON_REPRESENTANTES.csv'} ({len(df_est_export)} registros)")

        if not df_rep_export.empty:
            df_rep_export.to_csv(ruta_salida / "REPRESENTANTES.csv", index=False, encoding=Config.CODIFICACION_CSV, sep=Config.SEPARADOR_CSV)
            logger.info(f"✅ EXPORTACIÓN EXITOSA: {ruta_salida / 'REPRESENTANTES.csv'} ({len(df_rep_export)} registros)")
        else:
            logger.warning("❌ Archivo 'REPRESENTANTES.csv' no generado porque no se encontraron datos válidos.")
        
        print(proc_estudiantes.quality_report.generar_reporte())
    else:
        logger.error("❌ No se pudo extraer ningún dato de estudiante")

if __name__ == "__main__":
    main_estudiantes()
    