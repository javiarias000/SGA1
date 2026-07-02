"""
Importador de calificaciones desde el Excel oficial del Conservatorio.

Replica el formato que usaba `informe-whatsapp/Datos/` (column_map.json):
pestañas 1P, 2P, 3P, 4P (parciales), 1Q, 2Q (quimestres) y Contacto.
Las celdas combinadas del Excel original desalinean los headers respecto a
las filas de datos, por eso se usa un mapa de índices de columna en vez de
leer el texto del encabezado.
"""
import json
import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation

_COLUMN_MAP_PATH = os.path.join(os.path.dirname(__file__), 'data', 'column_map.json')
with open(_COLUMN_MAP_PATH, encoding='utf-8') as _f:
    COLUMN_MAP = json.load(_f)['sheets']

PARCIAL_SHEETS = ['1P', '2P', '3P', '4P']
QUIMESTRE_SHEETS = {'1Q': 'Q1', '2Q': 'Q2'}
PARCIALES_POR_QUIMESTRE = {'Q1': ('1P', '2P'), 'Q2': ('3P', '4P')}

CODIGO_TIPO_EXAMEN = 'examen_quimestral'
NOMBRE_TIPO_EXAMEN = 'Examen Quimestral'


def _normalizar(texto):
    """minúsculas, sin tildes, espacios colapsados — para emparejar nombres."""
    if not texto:
        return ''
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', texto).strip().lower()


def _parse_nota(valor):
    """Convierte '7,00' / '7.00' / 7 / None -> Decimal o None."""
    if valor is None or valor == '':
        return None
    if isinstance(valor, (int, float, Decimal)):
        return Decimal(str(valor)).quantize(Decimal('0.01'))
    texto = str(valor).strip().replace(',', '.')
    try:
        return Decimal(texto).quantize(Decimal('0.01'))
    except InvalidOperation:
        return None


def leer_hoja(ws, sheet_key):
    """Lee una pestaña openpyxl según column_map.json. Devuelve lista de dicts {col_name: valor}."""
    config = COLUMN_MAP.get(sheet_key)
    if not config:
        return []
    data_start = config['dataStartRow']  # índice de fila 0-based
    columnas = config['columns']
    filas = []
    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if row_idx < data_start:
            continue
        valores = {col['name']: (row[col['index']] if col['index'] < len(row) else None) for col in columnas}
        if not any(v not in (None, '') for v in valores.values()):
            continue
        filas.append(valores)
    return filas


def parse_workbook(wb):
    """wb: openpyxl Workbook. Devuelve {sheet_key: [filas...]} para las pestañas presentes."""
    return {key: leer_hoja(wb[key], key) for key in COLUMN_MAP if key in wb.sheetnames}


def _columnas_clase(fila):
    """Columnas 'Clase N1'/'Clase 1'/... de una fila de pestaña parcial, en orden, excluyendo el promedio."""
    return [(nombre, valor) for nombre, valor in fila.items() if re.match(r'(?i)^clase\b', nombre)]


def match_estudiantes(filas_hoja, enrollments):
    """Empareja cada fila (Apellidos+Nombres) contra los Enrollment de la Clase.

    Devuelve lista de tuplas (fila, enrollment_o_None).
    """
    candidatos = {_normalizar(enr.estudiante.nombre): enr for enr in enrollments if enr.estudiante}

    parejas = []
    for fila in filas_hoja:
        apellidos = (fila.get('Apellidos') or '').strip()
        nombres = (fila.get('Nombres') or '').strip()
        clave = _normalizar(f'{apellidos} {nombres}')
        enr = candidatos.get(clave) or candidatos.get(_normalizar(f'{nombres} {apellidos}'))
        if not enr:
            tokens = set(clave.split())
            for clave_candidato, candidato in candidatos.items():
                if tokens and tokens.issubset(set(clave_candidato.split())):
                    enr = candidato
                    break
        parejas.append((fila, enr))
    return parejas


def importar_calificaciones(clase, parsed, dry_run=True):
    """Importa calificaciones parciales + examen quimestral de un workbook ya parseado.

    `clase`: instancia de classes.models.Clase (define subject y enrollments destino).
    `parsed`: dict devuelto por parse_workbook().
    Devuelve un resumen: {estudiantes_emparejados, estudiantes_sin_match, notas_creadas,
    notas_actualizadas, telefonos_actualizados, sin_match: [nombres]}.
    """
    import contextlib
    from django.db import transaction
    from django.db.models.signals import post_save
    from classes.models import CalificacionParcial, Enrollment, TipoAporte
    from classes.signals import alerta_bajo_rendimiento

    enrollments = list(
        Enrollment.objects.filter(clase=clase, estado='ACTIVO').select_related('estudiante')
    )

    resumen = {
        'estudiantes_emparejados': 0,
        'sin_match': [],
        'notas_creadas': 0,
        'notas_actualizadas': 0,
        'telefonos_actualizados': 0,
    }

    tipo_aporte_cache = {}

    def get_tipo_aporte(nombre_col):
        if nombre_col not in tipo_aporte_cache:
            n = re.sub(r'(?i)^clase\s*n?', '', nombre_col).strip() or nombre_col
            codigo = f'clase_{_normalizar(n).replace(" ", "_")}'
            obj, _ = TipoAporte.objects.get_or_create(
                codigo=codigo,
                defaults={'nombre': f'Clase {n}', 'peso': Decimal('1.00')},
            )
            tipo_aporte_cache[nombre_col] = obj
        return tipo_aporte_cache[nombre_col]

    def get_tipo_aporte_examen():
        if CODIGO_TIPO_EXAMEN not in tipo_aporte_cache:
            obj, _ = TipoAporte.objects.get_or_create(
                codigo=CODIGO_TIPO_EXAMEN,
                defaults={'nombre': NOMBRE_TIPO_EXAMEN, 'peso': Decimal('0.00')},
            )
            tipo_aporte_cache[CODIGO_TIPO_EXAMEN] = obj
        return tipo_aporte_cache[CODIGO_TIPO_EXAMEN]

    def guardar(student, parcial, quimestre, tipo_aporte, nota):
        if dry_run:
            existe = CalificacionParcial.objects.filter(
                student=student, subject=clase.subject, parcial=parcial,
                quimestre=quimestre, tipo_aporte=tipo_aporte,
            ).exists()
            resumen['notas_actualizadas' if existe else 'notas_creadas'] += 1
            return
        _, created = CalificacionParcial.objects.update_or_create(
            student=student, subject=clase.subject, parcial=parcial,
            quimestre=quimestre, tipo_aporte=tipo_aporte,
            defaults={'calificacion': nota},
        )
        resumen['notas_creadas' if created else 'notas_actualizadas'] += 1

    sin_match_vistos = set()
    ctx = transaction.atomic() if not dry_run else contextlib.nullcontext()

    # Importar notas históricas no debe disparar alertas de WhatsApp en vivo a los
    # representantes (la señal post_save de CalificacionParcial sí debe seguir activa
    # para la entrada de notas normal de los docentes, fuera de esta importación masiva).
    if not dry_run:
        post_save.disconnect(alerta_bajo_rendimiento, sender=CalificacionParcial)

    try:
        with ctx:
            # ── Parciales (1P-4P): cada columna "Clase N#" -> una CalificacionParcial ──
            for sheet_key in PARCIAL_SHEETS:
                filas = parsed.get(sheet_key, [])
                if not filas:
                    continue
                quimestre = 'Q1' if sheet_key in ('1P', '2P') else 'Q2'
                parejas = match_estudiantes(filas, enrollments)
                for fila, enr in parejas:
                    nombre_fila = f"{fila.get('Apellidos', '')} {fila.get('Nombres', '')}".strip()
                    if not enr:
                        if nombre_fila and nombre_fila not in sin_match_vistos:
                            resumen['sin_match'].append(nombre_fila)
                            sin_match_vistos.add(nombre_fila)
                        continue
                    student = getattr(enr.estudiante, 'student_profile', None)
                    if not student:
                        continue
                    resumen['estudiantes_emparejados'] += 1
                    for nombre_col, valor in _columnas_clase(fila):
                        nota = _parse_nota(valor)
                        if nota is None:
                            continue
                        guardar(student, sheet_key, quimestre, get_tipo_aporte(nombre_col), nota)

            # ── Quimestres (1Q/2Q): solo el "EXAMEN QUIMESTRAL" (lo demás es derivado) ──
            for sheet_key, quimestre in QUIMESTRE_SHEETS.items():
                filas = parsed.get(sheet_key, [])
                if not filas:
                    continue
                parejas = match_estudiantes(filas, enrollments)
                parcial_destino = PARCIALES_POR_QUIMESTRE[quimestre][0]  # peso=0: no afecta el promedio del parcial
                for fila, enr in parejas:
                    if not enr:
                        continue
                    student = getattr(enr.estudiante, 'student_profile', None)
                    if not student:
                        continue
                    nota = _parse_nota(fila.get('EXAMEN QUIMESTRAL'))
                    if nota is None:
                        continue
                    guardar(student, parcial_destino, quimestre, get_tipo_aporte_examen(), nota)

            # ── Contacto: teléfono del representante, solo si está vacío ──
            for fila in parsed.get('Contacto', []):
                telefono = fila.get('Telefono')
                telefono = telefono.strip() if isinstance(telefono, str) else telefono
                if not telefono:
                    continue
                parejas = match_estudiantes([fila], enrollments)
                enr = parejas[0][1] if parejas else None
                if not enr:
                    continue
                student = getattr(enr.estudiante, 'student_profile', None)
                if not student or student.parent_phone:
                    continue
                if not dry_run:
                    student.parent_phone = str(telefono)
                    student.save(update_fields=['parent_phone'])
                resumen['telefonos_actualizados'] += 1
    finally:
        if not dry_run:
            post_save.connect(alerta_bajo_rendimiento, sender=CalificacionParcial)

    return resumen
