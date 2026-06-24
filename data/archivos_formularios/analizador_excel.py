import pandas as pd
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import unicodedata

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'etl_process_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================
class Config:
    """Configuración centralizada del sistema ETL"""
    
    # Configuración de exportación
    SEPARADOR_CSV = ';'
    CODIFICACION_CSV = 'utf-8-sig'  # Mejor soporte para Excel
    
    # Dominio institucional
    DOMINIO_DOCENTE = 'conservatoriobolivar.edu.ec'
    PASSWORD_DEFAULT = 'Cb2025$'
    
    # Patrones de validación
    PATRON_EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PATRON_CEDULA_EC = r'^\d{10}$'  # Cédulas ecuatorianas tienen 10 dígitos
    PATRON_CELULAR_EC = r'^09\d{8}$'  # Formato: 09XXXXXXXX
    
    # Hojas a omitir
    HOJAS_OMITIR = ['total', 'resumen', 'consolidado']
    
    # Mapeo de columnas
    MAPEO_COLUMNAS = {
        # Estudiantes
        'dirección_de_correo_electrónico': 'email_estudiante',
        'apellidos_del_estudiante': 'apellidos',
        'apellidos_del_estudiante_escribir_la_primera_letra_en_mayúsculas_y_las demás_en_minúsculas_por_ejemplo_pérez_lópez': 'apellidos',
        'nombres_del_estudiante': 'nombres',
        'apellidos_estudiante': 'apellidos',
        'nombres_estudiante': 'nombres',
        'año_de_estudio': 'grado',
        'curso': 'grado',
        'paralelo': 'paralelo',
        'no': 'id_temporal',
        'cedula': 'cedula',
        'cédula': 'cedula',
        'cedula_estudiante': 'cedula',
        
        # Representantes
        'nombres_completos_del_representante': 'rep_nombres',
        'apellidos_completos_del_representante': 'rep_apellidos',
        'número_de_cédula_del_representante': 'rep_cedula',
        'cedula_del_representante': 'rep_cedula',
        'celular_del_representante_padre_o_madre': 'rep_celular',
        'celular_representante': 'rep_celular',
        'correo_electrónico_del_representante': 'rep_email',
        'email_representante': 'rep_email',
        
        # Docentes
        'paralelo_señalar_el_mismo_paralelo_en_el_que_estuvieron_el_año_anterior': 'paralelo',
        'maestro_de_instrumento': 'teacher_name_instrumento',
        'docente_piano_acompanamiento': 'teacher_name_acompanamiento',
        'docente_piano_complementario': 'teacher_name_complementario',
        'docente': 'teacher_name', # Mapeo para docentes genéricos/Agrupación
        'profesor': 'teacher_name', # Mapeo para docentes genéricos/Agrupación
        
        # Especialización
        'instrumento_que_estudia_en_el_conservatorio_bolívar': 'specialization_instrument',
        'instrumento': 'specialization_instrument',
        'agrupación': 'specialization_group',
        'agrupacion': 'specialization_group',
    }

# =============================================================================
# CLASES AUXILIARES PARA LIMPIEZA Y VALIDACIÓN
# =============================================================================
class DataCleaner:
    """Clase para operaciones de limpieza de datos"""
    
    @staticmethod
    def normalizar_nombre_columna(nombre: str) -> str:
        """Normaliza nombres de columnas para búsqueda consistente"""
        if pd.isna(nombre):
            return 'sin_nombre'
        
        nombre = str(nombre).lower().strip()
        # Remover acentos
        nombre = unicodedata.normalize('NFKD', nombre)
        nombre = nombre.encode('ASCII', 'ignore').decode('ASCII')
        # Limpiar caracteres especiales
        nombre = re.sub(r'[^\w\s]', '', nombre)
        nombre = re.sub(r'\s+', '_', nombre)
        return nombre.strip('_')
    
    @staticmethod
    def normalizar_texto(texto: str, titulo: bool = False) -> str:
        """Normaliza texto general con opción de formato título"""
        if pd.isna(texto) or texto == '':
            return ''
        
        texto = str(texto).strip()
        texto = re.sub(r'\s+', ' ', texto)
        
        if titulo:
            # Formato: Primera Letra Mayúscula
            texto = texto.title()
        
        return texto
    
    @staticmethod
    def limpiar_email(email: str) -> str:
        """Limpia y normaliza emails"""
        if pd.isna(email):
            return ''
        
        email = str(email).lower().strip()
        # Remover espacios
        email = re.sub(r'\s+', '', email)
        return email
    
    @staticmethod
    def limpiar_cedula(cedula: str) -> str:
        """Limpia y normaliza cédulas"""
        if pd.isna(cedula):
            return ''
        
        # Extraer solo dígitos
        cedula = re.sub(r'\D', '', str(cedula))
        return cedula
    
    @staticmethod
    def limpiar_celular(celular: str) -> str:
        """Limpia y normaliza números de celular"""
        if pd.isna(celular):
            return ''
        
        # Extraer solo dígitos
        celular = re.sub(r'\D', '', str(celular))
        
        # Si tiene 9 dígitos, agregar 0 al inicio
        if len(celular) == 9 and celular[0] == '9':
            celular = '0' + celular
        
        return celular
    
    @staticmethod
    def generar_username_desde_nombre(nombre_completo: str, dominio: str = None) -> str:
        """Genera username/email desde nombre completo"""
        if pd.isna(nombre_completo) or nombre_completo == '':
            return ''
        
        # Normalizar y limpiar
        username = nombre_completo.lower().strip()
        # Remover acentos
        username = unicodedata.normalize('NFKD', username)
        username = username.encode('ASCII', 'ignore').decode('utf-8')
        # Solo letras y espacios
        username = re.sub(r'[^a-z\s]', '', username)
        # Reemplazar espacios con puntos
        username = re.sub(r'\s+', '.', username).strip('.')
        
        if dominio:
            return f"{username}@{dominio}"
        return username


class DataValidator:
    """Clase para validaciones de datos"""
    
    @staticmethod
    def validar_email(email: str) -> bool:
        """Valida formato de email"""
        if pd.isna(email) or email == '':
            return False
        return bool(re.match(Config.PATRON_EMAIL, str(email)))
    
    @staticmethod
    def validar_cedula_ecuatoriana(cedula: str) -> bool:
        """Valida cédula ecuatoriana (10 dígitos + dígito verificador)"""
        if pd.isna(cedula) or cedula == '':
            return False
        
        cedula = str(cedula).strip()
        
        if not re.match(Config.PATRON_CEDULA_EC, cedula):
            return False
        
        # Validación del dígito verificador
        try:
            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            suma = 0
            
            for i in range(9):
                valor = int(cedula[i]) * coeficientes[i]
                suma += valor if valor < 10 else valor - 9
            
            digito_verificador = (10 - (suma % 10)) % 10
            return digito_verificador == int(cedula[9])
        except:
            return False
    
    @staticmethod
    def validar_celular_ecuatoriano(celular: str) -> bool:
        """Valida número de celular ecuatoriano"""
        if pd.isna(celular) or celular == '':
            return False
        return bool(re.match(Config.PATRON_CELULAR_EC, str(celular)))


class DataQualityReport:
    """Genera reportes de calidad de datos"""
    
    def __init__(self):
        self.issues = []
    
    def add_issue(self, categoria: str, detalle: str, cantidad: int = 1):
        """Agrega un problema detectado"""
        self.issues.append({
            'categoria': categoria,
            'detalle': detalle,
            'cantidad': cantidad
        })
    
    def generar_reporte(self) -> str:
        """Genera reporte consolidado"""
        if not self.issues:
            return "✅ No se detectaron problemas de calidad"
        
        reporte = "\n📊 REPORTE DE CALIDAD DE DATOS:\n"
        reporte += "=" * 60 + "\n"
        
        for issue in self.issues:
            reporte += f"  ⚠️  {issue['categoria']}: {issue['detalle']} ({issue['cantidad']})\n"
        
        return reporte


# =============================================================================
# PROCESADORES DE DATOS POR ENTIDAD
# =============================================================================
class ProcesadorEstudiantes:
    """Procesador especializado para datos de estudiantes"""
    
    def __init__(self):
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.quality_report = DataQualityReport()
    
    def procesar(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        """Procesa hoja de estudiantes"""
        logger.info(f"Procesando estudiantes: {archivo_nombre} - Hoja '{sheet_name}'")
        
        # Verificar si es hoja a omitir
        if sheet_name.lower() in Config.HOJAS_OMITIR:
            logger.info(f"Hoja '{sheet_name}' omitida (resumen)")
            return None
        
        try:
            # Leer Excel
            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, engine='openpyxl')
            
            # Normalizar nombres de columnas
            df.columns = [self.cleaner.normalizar_nombre_columna(col) for col in df.columns]
            
            # Renombrar columnas según mapeo
            df = df.rename(columns={
                self.cleaner.normalizar_nombre_columna(k): v 
                for k, v in Config.MAPEO_COLUMNAS.items()
            })
            
            # Seleccionar columnas relevantes
            cols_estudiante = ['email_estudiante', 'apellidos', 'nombres', 'paralelo', 'grado', 'cedula', 'id_temporal']
            cols_representante = ['rep_nombres', 'rep_apellidos', 'rep_cedula', 'rep_celular', 'rep_email']
            
            cols_disponibles = [col for col in cols_estudiante + cols_representante if col in df.columns]
            df = df[cols_disponibles].copy()
            
            # === LIMPIEZA DE DATOS ESTUDIANTE ===
            
            # Email
            if 'email_estudiante' in df.columns:
                df['email'] = df['email_estudiante'].apply(self.cleaner.limpiar_email)
                # Validar emails
                emails_invalidos = df[~df['email'].apply(self.validator.validar_email) & (df['email'] != '')]
                if len(emails_invalidos) > 0:
                    self.quality_report.add_issue('Email Inválido', 'Estudiantes con email mal formado', len(emails_invalidos))
                    logger.warning(f"Se encontraron {len(emails_invalidos)} emails inválidos")
                
                # Filtrar registros sin email válido
                df = df[df['email'].apply(self.validator.validar_email)]
            else:
                logger.error(f"Columna 'email_estudiante' no encontrada en {sheet_name}")
                return None
            
            # Nombres completos
            if 'apellidos' in df.columns and 'nombres' in df.columns:
                df['apellidos'] = df['apellidos'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
                df['nombres'] = df['nombres'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
                df['full_name'] = df['apellidos'] + ' ' + df['nombres']
                df['full_name'] = df['full_name'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            else:
                logger.error(f"Columnas 'apellidos' o 'nombres' no encontradas en {sheet_name}")
                return None
            
            # Eliminar registros sin nombre
            df = df[df['full_name'].str.strip() != '']
            
            # Cédula
            if 'cedula' in df.columns:
                df['cedula'] = df['cedula'].apply(self.cleaner.limpiar_cedula)
                cedulas_invalidas = df[~df['cedula'].apply(self.validator.validar_cedula_ecuatoriana) & (df['cedula'] != '')]
                if len(cedulas_invalidas) > 0:
                    self.quality_report.add_issue('Cédula Inválida', 'Estudiantes con cédula mal formada', len(cedulas_invalidas))
                    logger.warning(f"Se encontraron {len(cedulas_invalidas)} cédulas inválidas")
            
            # Grado
            if 'grado' not in df.columns:
                # Extraer grado del nombre de la hoja
                grado_match = re.search(r'(\d+)', sheet_name)
                df['grado'] = grado_match.group(1) if grado_match else 'ND'
            
            df['grado'] = df['grado'].astype(str).str.strip()
            
            # Paralelo
            if 'paralelo' in df.columns:
                df['paralelo'] = df['paralelo'].astype(str).str.strip().str.upper()
            
            # === LIMPIEZA DE DATOS REPRESENTANTE ===
            
            # Nombres representante
            if 'rep_nombres' in df.columns:
                df['rep_nombres'] = df['rep_nombres'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            
            if 'rep_apellidos' in df.columns:
                df['rep_apellidos'] = df['rep_apellidos'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            
            # Email representante 
            if 'rep_email' in df.columns:
                df['rep_email'] = df['rep_email'].apply(self.cleaner.limpiar_email)
                rep_emails_invalidos = df[~df['rep_email'].apply(self.validator.validar_email) & (df['rep_email'] != '')]
                if len(rep_emails_invalidos) > 0:
                    self.quality_report.add_issue('Email Rep. Inválido', 'Representantes con email mal formado', len(rep_emails_invalidos))
            
            # Cédula representante
            if 'rep_cedula' in df.columns:
                df['rep_cedula'] = df['rep_cedula'].apply(self.cleaner.limpiar_cedula)
                rep_cedulas_invalidas = df[~df['rep_cedula'].apply(self.validator.validar_cedula_ecuatoriana) & (df['rep_cedula'] != '')]
                if len(rep_cedulas_invalidas) > 0:
                    self.quality_report.add_issue('Cédula Rep. Inválida', 'Representantes con cédula mal formada', len(rep_cedulas_invalidas))
            
            # Celular representante
            if 'rep_celular' in df.columns:
                df['rep_celular'] = df['rep_celular'].apply(self.cleaner.limpiar_celular)
                rep_celulares_invalidos = df[~df['rep_celular'].apply(self.validator.validar_celular_ecuatoriano) & (df['rep_celular'] != '')]
                if len(rep_celulares_invalidos) > 0:
                    self.quality_report.add_issue('Celular Rep. Inválido', 'Representantes con celular mal formado', len(rep_celulares_invalidos))
            
            # Metadatos
            df['rol'] = 'ESTUDIANTE'
            df['source_file'] = archivo_nombre
            df['source_sheet'] = sheet_name
            
            logger.info(f"✅ Procesados {len(df)} estudiantes de '{sheet_name}'")
            return df.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"❌ Error procesando {sheet_name}: {str(e)}", exc_info=True)
            return None


class ProcesadorDocentes:
    """Procesador especializado para datos de docentes"""
    
    def __init__(self):
        self.cleaner = DataCleaner()
        self.quality_report = DataQualityReport()
    
    def procesar(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        """Extrae docentes únicos de archivos de distribución"""
        logger.info(f"Extrayendo docentes: {archivo_nombre} - Hoja '{sheet_name}'")
        
        try:
            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, engine='openpyxl')
            df.columns = [self.cleaner.normalizar_nombre_columna(col) for col in df.columns]
            
            # Renombrar columnas
            df = df.rename(columns={
                self.cleaner.normalizar_nombre_columna(k): v 
                for k, v in Config.MAPEO_COLUMNAS.items()
            })
            
            # Columnas de docentes
            cols_docentes = [
                'teacher_name_instrumento',
                'teacher_name_acompanamiento',
                'teacher_name_complementario',
                'teacher_name'
            ]
            
            # Extraer todos los nombres de docentes
            nombres_docentes = []
            cols_encontradas = []
            
            for col in cols_docentes:
                if col in df.columns:
                    nombres_docentes.extend(df[col].dropna().astype(str).tolist())
                    cols_encontradas.append(col)
            
            if not cols_encontradas:
                logger.warning(f"No se encontraron columnas de docentes en '{sheet_name}'")
                return None
            
            logger.info(f"Columnas de docentes encontradas: {cols_encontradas}")
            
            # Crear DataFrame de docentes únicos
            df_docentes = pd.DataFrame({'full_name_raw': nombres_docentes})
            
            # Limpiar nombres
            df_docentes['full_name'] = df_docentes['full_name_raw'].apply(
                lambda x: self.cleaner.normalizar_texto(x, titulo=True)
            )
            
            # Eliminar valores vacíos
            df_docentes = df_docentes[df_docentes['full_name'].str.strip() != '']
            df_docentes = df_docentes[df_docentes['full_name'] != 'Nan']
            
            # Generar emails
            df_docentes['email'] = df_docentes['full_name'].apply(
                lambda x: self.cleaner.generar_username_desde_nombre(x, Config.DOMINIO_DOCENTE)
            )
            
            # Eliminar duplicados
            df_docentes = df_docentes.drop_duplicates(subset=['email'], keep='first')
            
            # Metadatos
            df_docentes['rol'] = 'DOCENTE'
            df_docentes['username'] = df_docentes['email']
            df_docentes['password_plano'] = Config.PASSWORD_DEFAULT
            df_docentes['source_file'] = archivo_nombre
            df_docentes['source_sheet'] = sheet_name
            
            # Seleccionar columnas finales
            df_docentes = df_docentes[['full_name', 'email', 'username', 'password_plano', 'rol', 'source_file', 'source_sheet']]
            
            logger.info(f"✅ Extraídos {len(df_docentes)} docentes únicos")
            return df_docentes.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo docentes de {sheet_name}: {str(e)}", exc_info=True)
            return None


class ProcesadorAsignaciones:
    """Procesador especializado para asignaciones instrumento/agrupación"""
    
    def __init__(self):
        self.cleaner = DataCleaner()
    
    def procesar(self, archivo_nombre: str, ruta_archivo: str, sheet_name: str) -> Optional[pd.DataFrame]:
        """Extrae asignaciones de instrumento y agrupación"""
        logger.info(f"Extrayendo asignaciones: {archivo_nombre} - Hoja '{sheet_name}'")
        
        try:
            df = pd.read_excel(ruta_archivo, sheet_name=sheet_name, engine='openpyxl')
            df.columns = [self.cleaner.normalizar_nombre_columna(col) for col in df.columns]
            
            # Renombrar columnas
            df = df.rename(columns={
                self.cleaner.normalizar_nombre_columna(k): v 
                for k, v in Config.MAPEO_COLUMNAS.items()
            })
            
            # Generar nombre completo del estudiante (necesario para la unión)
            if 'apellidos' in df.columns and 'nombres' in df.columns:
                df['apellidos'] = df['apellidos'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
                df['nombres'] = df['nombres'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
                df['full_name'] = df['apellidos'] + ' ' + df['nombres']
                df['full_name'] = df['full_name'].apply(lambda x: self.cleaner.normalizar_texto(x, titulo=True))
            else:
                logger.warning(f"Faltan columnas de nombre para generar full_name en asignaciones de {sheet_name}")
                return None

            # === CONSOLIDAR NOMBRE DEL DOCENTE (FIX para Agrupaciones y Instrumento) ===
            # La meta es tener un solo 'teacher_name' que contenga el profesor asignado.
            
            # Columnas de docente posibles (prioritarias a la izquierda)
            teacher_cols_priority = [
                'teacher_name', # Mapeado de 'docente' o 'profesor'
                'teacher_name_instrumento', # Mapeado de 'maestro_de_instrumento'
                'teacher_name_acompanamiento', 
                'teacher_name_complementario'
            ]

            # Inicializar la columna final de nombre del docente
            df['teacher_name_final'] = pd.Series(index=df.index, dtype=str)
            
            for col in teacher_cols_priority:
                if col in df.columns:
                    # Usar fillna para llenar los valores nulos con el siguiente valor de columna
                    df['teacher_name_final'] = df['teacher_name_final'].fillna(df[col])

            # Renombrar la columna consolidada y limpiarla
            df['teacher_name'] = df['teacher_name_final'].apply(
                lambda x: self.cleaner.normalizar_texto(x, titulo=True)
            )
            
            # Limpieza y normalización de especialización
            if 'specialization_instrument' in df.columns:
                df['specialization_instrument'] = df['specialization_instrument'].apply(
                    lambda x: self.cleaner.normalizar_texto(x, titulo=True)
                )
            
            if 'specialization_group' in df.columns:
                df['specialization_group'] = df['specialization_group'].apply(
                    lambda x: self.cleaner.normalizar_texto(x, titulo=True)
                )
            
            # Grado y paralelo
            if 'grado' in df.columns:
                df['grado'] = df['grado'].astype(str).str.strip()
            
            if 'paralelo' in df.columns:
                df['paralelo'] = df['paralelo'].astype(str).str.strip().str.upper()
            
            # Seleccionar columnas relevantes
            cols_finales = [
                'full_name', 'grado', 'paralelo',
                'teacher_name', # <-- Columna con el nombre del docente consolidado
                'specialization_instrument', 
                'specialization_group'
            ]
            
            cols_disponibles = [col for col in cols_finales if col in df.columns]
            df = df[cols_disponibles].copy()
            
            # Eliminar filas vacías
            df = df[df['full_name'].str.strip() != '']
            
            # Metadatos
            df['source_file'] = archivo_nombre
            df['source_sheet'] = sheet_name
            
            logger.info(f"✅ Extraídas {len(df)} asignaciones de '{sheet_name}'")
            return df.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo asignaciones de {sheet_name}: {str(e)}", exc_info=True)
            return None


# =============================================================================
# CONSOLIDADOR Y GENERADOR DE ARCHIVOS FINALES
# =============================================================================
class ConsolidadorDatos:
    """Consolida y genera archivos finales relacionados"""
    
    def __init__(self, ruta_salida: str = './output'):
        self.ruta_salida = Path(ruta_salida)
        self.ruta_salida.mkdir(exist_ok=True)
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        
    def consolidar_y_exportar(self, 
                               datos_estudiantes: List[pd.DataFrame],
                               datos_docentes: List[pd.DataFrame],
                               datos_asignaciones: List[pd.DataFrame]):
        """Consolida todos los datos y genera archivos finales"""
        
        logger.info("\n" + "="*70)
        logger.info("INICIANDO CONSOLIDACIÓN Y GENERACIÓN DE ARCHIVOS FINALES")
        logger.info("="*70)
        
        # =====================================================================
        # 1. CONSOLIDAR ESTUDIANTES Y REPRESENTANTES
        # =====================================================================
        if datos_estudiantes:
            logger.info("\n📚 Consolidando estudiantes...")
            df_estudiantes = pd.concat(datos_estudiantes, ignore_index=True)
            
            # Eliminar duplicados por email (mantener el primero)
            duplicados_est = df_estudiantes.duplicated(subset=['email'], keep=False).sum()
            if duplicados_est > 0:
                logger.warning(f"⚠️  Se encontraron {duplicados_est} estudiantes duplicados (se mantendrá el primero)")
            
            df_estudiantes = df_estudiantes.drop_duplicates(subset=['email'], keep='first')
            
            # Generar username y password
            df_estudiantes['username'] = df_estudiantes['email']
            df_estudiantes['password_plano'] = Config.PASSWORD_DEFAULT
            
            # Separar datos de representantes
            cols_representante_limpias = [c for c in df_estudiantes.columns if c.startswith('rep_')]
            
            if cols_representante_limpias:
                df_representantes = df_estudiantes[['email', 'full_name'] + cols_representante_limpias].copy()
                df_representantes = df_representantes.drop_duplicates(subset=['email'])
                
                # Validar si 'rep_email' existe antes de usarla
                if 'rep_email' not in df_representantes.columns:
                    logger.warning("⚠️  La columna 'rep_email' no está presente en los datos de representantes consolidados")
                
                # Filtrar filas donde TODOS los datos de representante están vacíos
                df_representantes = df_representantes.dropna(subset=cols_representante_limpias, how='all')
            else:
                df_representantes = pd.DataFrame()
            
            logger.info(f"✅ Total estudiantes únicos: {len(df_estudiantes)}")
            logger.info(f"✅ Total representantes únicos (con datos): {len(df_representantes)}")
        else:
            logger.error("❌ No hay datos de estudiantes para consolidar")
            df_estudiantes = pd.DataFrame()
            df_representantes = pd.DataFrame()
        
        # =====================================================================
        # 2. CONSOLIDAR DOCENTES
        # =====================================================================
        if datos_docentes:
            logger.info("\n👨‍🏫 Consolidando docentes...")
            df_docentes = pd.concat(datos_docentes, ignore_index=True)
            
            # Eliminar duplicados por email
            duplicados_doc = df_docentes.duplicated(subset=['email'], keep=False).sum()
            if duplicados_doc > 0:
                logger.warning(f"⚠️  Se encontraron {duplicados_doc} docentes duplicados (se mantendrá el primero)")
            
            df_docentes = df_docentes.drop_duplicates(subset=['email'], keep='first')
            
            logger.info(f"✅ Total docentes únicos: {len(df_docentes)}")
        else:
            logger.error("❌ No hay datos de docentes para consolidar")
            df_docentes = pd.DataFrame()
        
        # =====================================================================
        # CONSOLIDAR ASIGNACIONES
        # =====================================================================
        if datos_asignaciones:
            logger.info("\n📋 Consolidando asignaciones...")
            try:
                df_asignaciones = pd.concat(datos_asignaciones, ignore_index=True)
                df_asignaciones = df_asignaciones.drop_duplicates()
                logger.info(f"✅ Total asignaciones: {len(df_asignaciones)}")
            except ValueError:
                logger.warning("⚠️  No se pudieron consolidar asignaciones (lista vacía)")
                df_asignaciones = pd.DataFrame()
        else:
            logger.warning("⚠️  No hay datos de asignaciones")
            df_asignaciones = pd.DataFrame()
        
        # =====================================================================
        # RELACIONAR DATOS Y GENERAR ARCHIVOS FINALES
        # =====================================================================
        
        # ARCHIVO 1: DOCENTES
        archivo_docentes = self._generar_archivo_docentes(df_docentes)
        
        # ARCHIVO 2: ESTUDIANTES CON REPRESENTANTES
        archivo_estudiantes = self._generar_archivo_estudiantes(df_estudiantes, df_representantes)
        
        # ARCHIVO 3 y 4: INSTRUMENTO Y AGRUPACIONES CON RELACIONES
        archivo_instrumento, archivo_agrupacion = self._generar_archivos_asignaciones(
            df_asignaciones, df_estudiantes, df_docentes
        )
        
        # ARCHIVO 5: REPRESENTANTES ÚNICOS
        archivo_representantes = self._generar_archivo_representantes(df_representantes)
        
        # =====================================================================
        # EXPORTAR ARCHIVOS
        # =====================================================================
        self._exportar_archivos({
            'DOCENTES': archivo_docentes,
            'ESTUDIANTES_CON_REPRESENTANTES': archivo_estudiantes,
            'INSTRUMENTO_ASIGNACIONES': archivo_instrumento,
            'AGRUPACION_ASIGNACIONES': archivo_agrupacion,
            'REPRESENTANTES': archivo_representantes
        })
        
        # =====================================================================
        # REPORTE FINAL
        # =====================================================================
        self._generar_reporte_final(archivo_docentes, archivo_estudiantes, 
                                     archivo_instrumento, archivo_agrupacion, 
                                     archivo_representantes)
    
    def _generar_archivo_docentes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera archivo final de docentes"""
        if df.empty:
            return df
        
        cols_orden = ['full_name', 'email', 'username', 'password_plano', 'rol']
        cols_disponibles = [c for c in cols_orden if c in df.columns]
        
        return df[cols_disponibles].sort_values('full_name').reset_index(drop=True)
    
    def _generar_archivo_estudiantes(self, df_est: pd.DataFrame, df_rep: pd.DataFrame) -> pd.DataFrame:
        """Genera archivo de estudiantes con datos de representantes"""
        if df_est.empty:
            return df_est
        
        # Unir con representantes
        if not df_rep.empty:
            # Seleccionar solo las columnas de rep_ para la unión
            cols_rep = [c for c in df_rep.columns if c.startswith('rep_')]
            
            df_final = pd.merge(
                df_est,
                df_rep[['email', 'full_name'] + cols_rep],
                on=['email', 'full_name'],
                how='left',
                suffixes=('', '_rep_dup')
            )
        else:
            df_final = df_est.copy()
        
        # Ordenar columnas
        cols_estudiante = ['full_name', 'email', 'username', 'password_plano', 'cedula', 
                           'grado', 'paralelo', 'rol']
        cols_representante = ['rep_nombres', 'rep_apellidos', 'rep_cedula', 
                              'rep_celular', 'rep_email']
        
        cols_orden = cols_estudiante + cols_representante
        cols_disponibles = [c for c in cols_orden if c in df_final.columns]
        
        return df_final[cols_disponibles].sort_values(['grado', 'paralelo', 'full_name']).reset_index(drop=True)
    
    def _generar_archivos_asignaciones(self, df_asig: pd.DataFrame, 
                                        df_est: pd.DataFrame, 
                                        df_doc: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Genera archivos de asignaciones de instrumento y agrupación"""
        
        if df_asig.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        # Relacionar con estudiantes para obtener email y asegurar grado/paralelo
        df_asig_est = pd.merge(
            df_asig,
            df_est[['full_name', 'email', 'grado', 'paralelo']].drop_duplicates(subset=['full_name']),
            on='full_name',
            how='left',
            suffixes=('_asig', '_est')
        )
        
        # Relacionar con docentes para obtener email del docente
        if 'teacher_name' in df_asig_est.columns:
            # La columna 'teacher_name' en df_asig_est ahora contiene el nombre consolidado
            df_asig_completo = pd.merge(
                df_asig_est,
                df_doc[['full_name', 'email']].rename(columns={'full_name': 'teacher_name', 'email': 'teacher_email'}),
                on='teacher_name',
                how='left'
            )
        else:
            df_asig_completo = df_asig_est.copy()
            df_asig_completo['teacher_email'] = None
        
        # Archivo de Instrumento (mantiene email de estudiante y docente)
        df_instrumento = df_asig_completo[df_asig_completo['specialization_instrument'].notna()].copy()
        cols_instrumento = ['teacher_name', 'teacher_email', 'full_name', 'email', 
                            'grado', 'paralelo', 'specialization_instrument']
        cols_disponibles_inst = [c for c in cols_instrumento if c in df_instrumento.columns]
        df_instrumento = df_instrumento[cols_disponibles_inst].sort_values(
            ['teacher_name', 'specialization_instrument', 'full_name']
        ).reset_index(drop=True)
        
        # Archivo de Agrupación (MODIFICADO: Elimina emails de estudiante y docente)
        df_agrupacion = df_asig_completo[df_asig_completo['specialization_group'].notna()].copy()
        
        # Columnas solicitadas: Nombre Docente, Nombre Estudiante, Grado. Se mantiene Paralelo y Agrupación.
        cols_agrupacion = [
            'teacher_name',         # Nombre del docente (Requerido)
            'full_name',            # Nombre del estudiante
            'grado',                # Año/Grado (Requerido)
            'paralelo',             # Paralelo (Útil para contexto)
            'specialization_group'  # Nombre de la agrupación
            # 'teacher_email' y 'email' se ELIMINAN
        ]
        
        cols_disponibles_agrup = [c for c in cols_agrupacion if c in df_agrupacion.columns]
        df_agrupacion = df_agrupacion[cols_disponibles_agrup].sort_values(
            ['teacher_name', 'specialization_group', 'full_name']
        ).reset_index(drop=True)
        
        return df_instrumento, df_agrupacion
    
    def _generar_archivo_representantes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera archivo de representantes únicos"""
        if df.empty:
            logger.warning("⚠️  El DataFrame de representantes está vacío")
            return df

        # Columnas disponibles
        has_cedula = 'rep_cedula' in df.columns
        has_email = 'rep_email' in df.columns
        
        if not has_cedula and not has_email:
            logger.warning("⚠️  No se encontraron columnas 'rep_cedula' ni 'rep_email' para generar ID único de representante")
            return pd.DataFrame()

        # Generar ID único por representante (basado en cédula y/o email)
        if has_cedula and has_email:
            # Priorizar cédula si existe, si no, usar email
            # FIX: Asegurar que el rep_email exista en la columna antes de usar
            df['rep_id'] = df.get('rep_cedula', pd.Series()).fillna(df.get('rep_email', pd.Series()))
        elif has_cedula:
            df['rep_id'] = df.get('rep_cedula', pd.Series())
        elif has_email:
            df['rep_id'] = df.get('rep_email', pd.Series())
        
        # Eliminar duplicados
        df = df.dropna(subset=['rep_id'])
        df = df.drop_duplicates(subset=['rep_id'], keep='first').drop(columns=['rep_id'])

        # Seleccionar columnas finales
        cols_orden = ['rep_nombres', 'rep_apellidos', 'rep_cedula', 'rep_celular', 'rep_email']
        cols_disponibles = [c for c in cols_orden if c in df.columns]

        return df[cols_disponibles].sort_values('rep_apellidos').reset_index(drop=True)
    
    def _exportar_archivos(self, archivos: Dict[str, pd.DataFrame]):
        """Exporta todos los archivos a CSV"""
        logger.info("\n💾 Exportando archivos CSV...")
        
        for nombre, df in archivos.items():
            if df.empty:
                logger.warning(f"⚠️  Archivo '{nombre}' está vacío, se omite exportación")
                continue
            
            ruta_archivo = self.ruta_salida / f"{nombre}.csv"
            df.to_csv(
                ruta_archivo,
                index=False,
                encoding=Config.CODIFICACION_CSV,
                sep=Config.SEPARADOR_CSV
            )
            logger.info(f"✅ Exportado: {ruta_archivo} ({len(df)} registros)")
    
    def _generar_reporte_final(self, df_doc, df_est, df_inst, df_agrup, df_rep):
        """Genera reporte final de consolidación"""
        logger.info("\n" + "="*70)
        logger.info("📊 RESUMEN FINAL DE CONSOLIDACIÓN")
        logger.info("="*70)
        logger.info(f"👨‍🏫 Docentes únicos: {len(df_doc)}")
        logger.info(f"👨‍🎓 Estudiantes únicos: {len(df_est)}")
        logger.info(f"👪 Representantes únicos: {len(df_rep)}")
        logger.info(f"🎼 Asignaciones de Instrumento: {len(df_inst)}")
        logger.info(f"🎵 Asignaciones de Agrupación: {len(df_agrup)}")
        logger.info("="*70)
        logger.info(f"📁 Archivos generados en: {self.ruta_salida.absolute()}")
        logger.info("="*70 + "\n")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal del ETL"""
    
    print("\n" + "="*70)
    print("🎓 SISTEMA ETL - INSTITUCIÓN EDUCATIVA CONSERVATORIO BOLÍVAR")
    print("="*70)
    
    # Solicitar ruta de trabajo
    print(f"\n📂 Carpeta actual: {os.getcwd()}")
    ruta_trabajo = input("Ingrese la ruta completa de la carpeta con archivos Excel: ").strip()
    
    if not os.path.exists(ruta_trabajo):
        logger.error(f"❌ La ruta '{ruta_trabajo}' no existe")
        return
    
    # Listar archivos Excel
    archivos_excel = [f for f in os.listdir(ruta_trabajo) if f.endswith(('.xlsx', '.xls'))]
    
    if not archivos_excel:
        logger.error(f"❌ No se encontraron archivos Excel en '{ruta_trabajo}'")
        return
    
    print(f"\n📚 Archivos Excel encontrados ({len(archivos_excel)}):")
    for i, archivo in enumerate(archivos_excel, 1):
        tipo = ""
        if 'Matriculados' in archivo or 'matriculados' in archivo:
            tipo = " [ESTUDIANTES]"
        elif 'Distribucion' in archivo or 'distribucion' in archivo:
            tipo = " [DOCENTES/ASIGNACIONES]"
        print(f"  [{i}] {archivo}{tipo}")
    
    # Selección de archivos
    print("\n💡 Opciones:")
    print("  - Ingrese números separados por coma (ej: 1,2,3)")
    print("  - Ingrese 'A' para procesar TODOS los archivos")
    
    seleccion = input("Su selección: ").strip().upper()
    
    if seleccion == 'A':
        archivos_procesar = archivos_excel
    else:
        try:
            indices = [int(x.strip()) for x in seleccion.split(',')]
            archivos_procesar = [archivos_excel[i-1] for i in indices if 1 <= i <= len(archivos_excel)]
        except:
            logger.error("❌ Selección inválida")
            return
    
    if not archivos_procesar:
        logger.error("❌ No se seleccionaron archivos válidos")
        return
    
    logger.info(f"\n✅ Se procesarán {len(archivos_procesar)} archivo(s)")
    
    # Inicializar procesadores
    proc_estudiantes = ProcesadorEstudiantes()
    proc_docentes = ProcesadorDocentes()
    proc_asignaciones = ProcesadorAsignaciones()
    
    # Almacenar datos procesados
    datos_estudiantes = []
    datos_docentes = []
    datos_asignaciones = []
    
    # Procesar archivos
    for archivo in archivos_procesar:
        ruta_completa = os.path.join(ruta_trabajo, archivo)
        logger.info(f"\n{'='*70}")
        logger.info(f"📄 Procesando: {archivo}")
        logger.info(f"{'='*70}")
        
        try:
            xls = pd.ExcelFile(ruta_completa, engine='openpyxl')
            
            for sheet_name in xls.sheet_names:
                
                if 'Matriculados' in archivo or 'matriculados' in archivo:
                    # Procesar estudiantes
                    df_temp = proc_estudiantes.procesar(archivo, ruta_completa, sheet_name)
                    if df_temp is not None:
                        datos_estudiantes.append(df_temp)
                
                elif 'Distribucion' in archivo or 'distribucion' in archivo:
                    # Procesar docentes
                    df_doc = proc_docentes.procesar(archivo, ruta_completa, sheet_name)
                    if df_doc is not None:
                        datos_docentes.append(df_doc)
                    
                    # Procesar asignaciones
                    df_asig = proc_asignaciones.procesar(archivo, ruta_completa, sheet_name)
                    if df_asig is not None:
                        datos_asignaciones.append(df_asig)
        
        except Exception as e:
            logger.error(f"❌ Error procesando archivo {archivo}: {str(e)}", exc_info=True)
    
    # Consolidar y exportar
    if datos_estudiantes or datos_docentes or datos_asignaciones:
        consolidador = ConsolidadorDatos(ruta_salida='./output')
        consolidador.consolidar_y_exportar(datos_estudiantes, datos_docentes, datos_asignaciones)
        
        # Mostrar reportes de calidad
        if hasattr(proc_estudiantes, 'quality_report'):
            print(proc_estudiantes.quality_report.generar_reporte())
    else:
        logger.error("❌ No se pudo procesar ningún dato")
    
    logger.info("\n✅ Proceso ETL finalizado")


if __name__ == "__main__":
    main()
    