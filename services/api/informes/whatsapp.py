"""
Cliente Python para Evolution API (WhatsApp).
Porta la lógica de informe-whatsapp/server.js → sección Evolution API.
"""
import re
import requests
from django.conf import settings


def _base_url() -> str:
    return (getattr(settings, 'EVOLUTION_API_URL', '') or '').rstrip('/')


def _headers() -> dict:
    return {
        'apikey': getattr(settings, 'EVOLUTION_API_KEY', ''),
        'Content-Type': 'application/json',
    }


def normalize_phone(raw: str) -> str | None:
    """Normaliza un número de teléfono ecuatoriano a formato 593XXXXXXXXX."""
    digits = re.sub(r'\D', '', str(raw or ''))
    if not digits:
        return None
    if digits.startswith('593'):
        return digits
    if digits.startswith('0'):
        return '593' + digits[1:]
    if len(digits) == 9:
        return '593' + digits
    return digits


def create_instance(instance_name: str) -> dict:
    """Crea o reconecta una instancia WhatsApp y devuelve el QR en base64."""
    url = _base_url()
    headers = _headers()

    # Intentar crear (si ya existe Evolution retorna error, se ignora)
    try:
        requests.post(f'{url}/instance/create', json={
            'instanceName': instance_name,
            'qrcode': True,
            'integration': 'WHATSAPP-BAILEYS',
        }, headers=headers, timeout=15)
    except Exception:
        pass

    try:
        r = requests.get(f'{url}/instance/connect/{instance_name}', headers=headers, timeout=15)
        payload = r.json()
        base64_qr = (
            payload.get('qrcode', {}).get('base64')
            or payload.get('base64')
        )
        return {'success': True, 'qr': base64_qr, 'raw': payload}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_instance_status(instance_name: str) -> dict:
    """Devuelve el estado de conexión de la instancia."""
    url = _base_url()
    try:
        r = requests.get(
            f'{url}/instance/connectionState/{instance_name}',
            headers=_headers(),
            timeout=10,
        )
        data = r.json()
        state = (
            data.get('instance', {}).get('state')
            or data.get('state')
            or data.get('connectionStatus')
            or 'unknown'
        )
        return {'success': True, 'state': state}
    except Exception as e:
        return {'success': False, 'state': 'close', 'error': str(e)}


def send_text(instance_name: str, phone: str, message: str) -> dict:
    """Envía un mensaje de texto via WhatsApp."""
    url = _base_url()
    try:
        r = requests.post(
            f'{url}/message/sendText/{instance_name}',
            json={'number': phone, 'text': message},
            headers=_headers(),
            timeout=30,
        )
        return {'success': True, 'data': r.json()}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Generadores de mensaje (porta buildParentMessage de server.js) ─────────────

def _fmt(v) -> str:
    try:
        return f'{float(v):.2f}' if v is not None and v != '' else '—'
    except (TypeError, ValueError):
        return '—'


def build_parent_message(student: dict, materia: str, periodo: str, docente_nombre: str) -> str:
    """
    Construye el mensaje WhatsApp para el representante.

    student debe contener:
      nombre, curso, nota (float), escala_cualitativa (str opcional),
      faltas_justificadas (int), faltas_injustificadas (int),
      asistencias (int, solo A1-A4), total_clases (int, solo A1-A4),
      pct_asistencia (float, solo A1-A4)
    """
    nombre = student.get('nombre', '—')
    curso = student.get('curso', '—')
    firma = f'\n\n_Atentamente,_\n_{docente_nombre or "Docente"}_\n_Conservatorio Bolívar de Ambato_'

    # ── Asistencia (A1-A4) ────────────────────────────────────────────────────
    if periodo in ('A1', 'A2', 'A3', 'A4'):
        reg_label = {
            'A1': '1er Parcial', 'A2': '2do Parcial',
            'A3': '3er Parcial', 'A4': '4to Parcial',
        }[periodo]
        asistencias = student.get('asistencias', 0)
        faltas_j = student.get('faltas_justificadas', 0)
        faltas_i = student.get('faltas_injustificadas', 0)
        total = student.get('total_clases', 0)
        pct = student.get('pct_asistencia', 0.0)

        msg = (
            f'📚 *Conservatorio Bolívar de Ambato*\n'
            f'_Informe de asistencias — Registro {periodo}_\n\n'
            f'Estimado/a representante de *{nombre}*:\n'
            f'🎓 Curso: {curso} | 📖 Asignatura: {materia}\n\n'
            f'📅 *Asistencias [{reg_label}]:*\n'
            f'• Clases registradas: {total}\n'
            f'• Asistencias: {asistencias}\n'
            f'• Faltas justificadas: {faltas_j}\n'
            f'• Faltas injustificadas: {faltas_i}\n'
            f'• Porcentaje: {pct:.1f}%\n'
        )

        if faltas_i >= 3:
            msg += '\n⚠️ *Registra inasistencias injustificadas.* Le invitamos a comunicarse con la institución.\n'
        elif pct < 75:
            msg += '\n⚠️ *Bajo porcentaje de asistencia.*\n'
        else:
            msg += '\n✅ Asistencia regular.\n'

        return msg + firma

    # ── Calificaciones ────────────────────────────────────────────────────────
    nota = student.get('nota', 0)
    escala = student.get('escala_cualitativa', '')
    faltas_j = student.get('faltas_justificadas', 0)
    faltas_i = student.get('faltas_injustificadas', 0)
    estado = student.get('estado', 'APROBADO')

    periodo_label = {
        '1P': 'Primer Parcial', '2P': 'Segundo Parcial',
        '3P': 'Tercer Parcial', '4P': 'Cuarto Parcial',
        '1Q': 'Primer Quimestre', '2Q': 'Segundo Quimestre',
        'Anual': 'Nota Anual',
    }.get(periodo, periodo)

    msg = (
        f'📚 *Conservatorio Bolívar de Ambato*\n'
        f'_Informe de calificaciones — {periodo_label}_\n\n'
        f'Estimado/a representante de *{nombre}*:\n'
        f'🎓 Curso: {curso}  |  📖 Asignatura: {materia}\n\n'
        f'📊 *Calificaciones {periodo_label}:*\n'
    )

    if periodo in ('1P', '2P', '3P', '4P'):
        msg += f'• Promedio: *{_fmt(nota)}*\n'

    elif periodo in ('1Q', '2Q'):
        p1 = student.get('p1')
        p2 = student.get('p2')
        prom_parciales = student.get('prom_parciales')
        examen = student.get('examen')
        if p1 is not None:
            msg += f'• 1er Parcial: {_fmt(p1)}\n'
        if p2 is not None:
            msg += f'• 2do Parcial: {_fmt(p2)}\n'
        if prom_parciales is not None:
            msg += f'• Prom. Parciales: {_fmt(prom_parciales)}\n'
        if examen is not None:
            msg += f'• Examen Quimestral: {_fmt(examen)}\n'
        msg += f'• *Nota Final: {_fmt(nota)}*'
        if escala:
            msg += f' ({escala})'
        msg += '\n'
        if faltas_j or faltas_i:
            msg += f'\n📅 *Asistencia:*\n'
            if faltas_j:
                msg += f'• Justificadas: {faltas_j}\n'
            if faltas_i:
                msg += f'• Injustificadas: {faltas_i}\n'

    elif periodo == 'Anual':
        q1 = student.get('q1')
        q2 = student.get('q2')
        if q1 is not None:
            msg += f'• 1er Quimestre: {_fmt(q1)}\n'
        if q2 is not None:
            msg += f'• 2do Quimestre: {_fmt(q2)}\n'
        msg += f'• *Nota Final Anual: {_fmt(nota)}*'
        if escala:
            msg += f' ({escala})'
        msg += '\n'
        if faltas_j or faltas_i:
            msg += f'\n📅 *Asistencia anual:*\n'
            if faltas_j:
                msg += f'• Justificadas: {faltas_j}\n'
            if faltas_i:
                msg += f'• Injustificadas: {faltas_i}\n'

    msg += (
        '\n⚠️ *Su representado/a presenta dificultades académicas.* '
        'Le invitamos a comunicarse con la institución.\n'
        if estado == 'DIFICULTAD'
        else '\n✅ Aprobado/a en esta etapa.\n'
    )

    return msg + firma
