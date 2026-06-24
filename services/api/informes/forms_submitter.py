"""
Envío de informes docentes al Google Form institucional.
Porta la lógica de /api/submit-forms y /api/submissions/:id/resend-form de server.js.
"""
import time
import requests


def submit_form(submission: dict, form_url: str, form_fields: list) -> dict:
    """
    Envía un registro al Google Form.

    submission debe contener:
      dropdown_option, docente, materia, contenidos, dificultades (list),
      acciones, form_text (texto completo combinado, opcional)

    form_fields: lista de {'entryId': int, 'mapping': str}
    """
    target_url = form_url.strip().replace('/viewform', '/formResponse')
    params = {}

    if form_fields:
        for field in form_fields:
            mapping = field.get('mapping', '')
            entry_id = field.get('entryId')
            if not entry_id:
                continue

            if mapping == 'auto_curso':
                value = submission.get('dropdown_option', '')
            elif mapping == 'text_docente':
                value = submission.get('docente', '')
            elif mapping == 'auto_materia':
                value = submission.get('materia', '')
            elif mapping == 'text_contenidos':
                value = submission.get('contenidos', '')
            elif mapping == 'auto_dificultades':
                difs = submission.get('dificultades', [])
                value = (
                    '\n'.join(f"- {d['nombre']} ({d['nota']}/10)" for d in difs)
                    if difs else 'Ninguno'
                )
            elif mapping == 'text_acciones':
                difs = submission.get('dificultades', [])
                value = submission.get('acciones', '') if difs else 'No aplica'
            elif mapping == 'informe_completo':
                value = submission.get('form_text', '')
            elif mapping == 'ignore':
                continue
            else:
                value = ''

            if value is not None:
                params[f'entry.{entry_id}'] = value
    else:
        # Fallback con entradas hardcoded del form original
        params['entry.1403373118'] = submission.get('dropdown_option', '')
        params['entry.697644543'] = submission.get('docente', '')
        params['entry.2132854786'] = submission.get('materia', '')
        params['entry.411694821'] = submission.get('form_text', '')

    params['fvv'] = '1'
    params['draftResponse'] = '[]'
    params['pageHistory'] = '0'
    import random
    params['fbzx'] = str(int(random.random() * 1e16))

    try:
        response = requests.post(
            target_url,
            data=params,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            allow_redirects=False,
            timeout=30,
        )
        # Google Forms devuelve 302 en éxito
        success = response.status_code < 400
        return {'success': success, 'status_code': response.status_code}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def build_form_text(contenidos: str, dificultades: list, acciones: str) -> str:
    """Construye el texto combinado del formulario (campo informe_completo)."""
    lines = [
        '1 - Contenidos trabajados en el 2do quimestre:',
        contenidos,
        '',
        '2 - Apellidos y nombres del estudiante que presente dificultades académicas o faltas:',
    ]
    if not dificultades:
        lines.append('Ninguno')
    else:
        for d in dificultades:
            lines.append(f"- {d['nombre']} (promedio: {d['nota']}/10)")
    lines.extend([
        '',
        '3 - Actividades realizadas:',
        'No aplica' if not dificultades else acciones,
    ])
    return '\n'.join(lines)
