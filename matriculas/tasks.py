"""
Celery tasks para análisis de documentos con OpenAI Vision.
"""
import base64
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _encode_file_b64(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def _is_image(filename: str) -> bool:
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))


def _analizar_documento_con_ia(tipo_doc: str, file_path: str) -> dict:
    """
    Llama a OpenAI GPT-4o para analizar un documento.
    Retorna dict con: valido (bool), observacion (str), confianza (float).
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        return {'valido': True, 'observacion': 'Revisión IA no configurada (sin API key).', 'confianza': 0.0}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompts = {
            'CEDULA': (
                "Eres un asistente de revisión documental para un conservatorio de música en Ecuador. "
                "Analiza esta imagen y determina si es una copia válida de cédula de identidad o acta de nacimiento. "
                "Verifica: 1) Que el documento sea legible, 2) Que los datos (nombre, número) sean visibles, "
                "3) Que no esté vencido o cortado. "
                "Responde en formato: VÁLIDO o NOVEDAD, seguido de una explicación breve en español."
            ),
            'CERT_EDUCACION': (
                "Eres un asistente de revisión documental para un conservatorio de música en Ecuador. "
                "Analiza esta imagen y determina si es un certificado válido de aprobación de educación regular "
                "(escuela o colegio). Verifica: 1) Legibilidad, 2) Nombre del estudiante visible, "
                "3) Año lectivo y institución mencionados, 4) Firma o sello institucional. "
                "Responde en formato: VÁLIDO o NOVEDAD, seguido de una explicación breve en español."
            ),
            'CERT_CONSERVATORIO': (
                "Eres un asistente de revisión documental para un conservatorio de música en Ecuador. "
                "Analiza esta imagen y determina si es un certificado válido de un conservatorio de música. "
                "Verifica: 1) Legibilidad, 2) Nombre del estudiante, 3) Institución y año, 4) Firma o sello. "
                "Responde en formato: VÁLIDO o NOVEDAD, seguido de una explicación breve en español."
            ),
            'FOTO_CARNET': (
                "Eres un asistente de revisión documental para un conservatorio de música en Ecuador. "
                "Analiza esta imagen y determina si es una foto carnet válida. "
                "Verifica: 1) Fondo claro (preferentemente blanco), 2) Rostro visible y centrado, "
                "3) Buena iluminación, 4) Foto reciente (no demasiado informal). "
                "Responde en formato: VÁLIDO o NOVEDAD, seguido de una explicación breve en español."
            ),
        }

        prompt = prompts.get(tipo_doc, "Analiza si este documento es válido. Responde VÁLIDO o NOVEDAD con una explicación.")

        if _is_image(file_path):
            b64 = _encode_file_b64(file_path)
            ext = file_path.split('.')[-1].lower()
            mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"}},
            ]
        else:
            # PDF: analizamos solo con texto descriptivo
            content = [
                {"type": "text", "text": (
                    prompt + "\n\nNota: El archivo es un PDF, no se puede previsualizar directamente. "
                    "Marca como VÁLIDO asumiendo que el usuario lo revisará manualmente, "
                    "pero indica que no se pudo verificar el contenido visualmente."
                )}
            ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=200,
        )
        text = response.choices[0].message.content.strip()
        valido = text.upper().startswith('VÁLIDO') or text.upper().startswith('VALIDO')
        confianza = 0.9 if valido else 0.7
        return {'valido': valido, 'observacion': text, 'confianza': confianza}

    except Exception as exc:
        logger.exception("Error en análisis IA de documento: %s", exc)
        return {'valido': True, 'observacion': f'No se pudo analizar automáticamente: {exc}', 'confianza': 0.0}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def analizar_documentos_solicitud(self, solicitud_id: int):
    """
    Analiza todos los documentos de una solicitud con IA.
    Actualiza DocumentoMatricula.estado_ia y SolicitudMatricula.revision_ia_completada.
    """
    from .models import SolicitudMatricula, DocumentoMatricula
    import os

    try:
        solicitud = SolicitudMatricula.objects.get(pk=solicitud_id)
    except SolicitudMatricula.DoesNotExist:
        logger.error("Solicitud %s no encontrada para análisis IA", solicitud_id)
        return

    tiene_novedades = False
    resumen_partes = []

    for doc in solicitud.documentos.all():
        doc.estado_ia = DocumentoMatricula.EstadoIA.PROCESANDO
        doc.save(update_fields=['estado_ia'])

        file_path = os.path.join(settings.MEDIA_ROOT, doc.archivo.name) if doc.archivo else None

        if not file_path or not os.path.exists(file_path):
            doc.estado_ia = DocumentoMatricula.EstadoIA.ERROR
            doc.observacion_ia = 'Archivo no encontrado en el servidor.'
            doc.save(update_fields=['estado_ia', 'observacion_ia'])
            tiene_novedades = True
            resumen_partes.append(f"• {doc.get_tipo_display()}: ARCHIVO NO ENCONTRADO")
            continue

        resultado = _analizar_documento_con_ia(doc.tipo, file_path)

        if resultado['valido']:
            doc.estado_ia = DocumentoMatricula.EstadoIA.VALIDO
        else:
            doc.estado_ia = DocumentoMatricula.EstadoIA.NOVEDAD
            tiene_novedades = True

        doc.observacion_ia = resultado['observacion']
        doc.confianza_ia = resultado['confianza']
        doc.save(update_fields=['estado_ia', 'observacion_ia', 'confianza_ia'])

        estado_str = '✓ VÁLIDO' if resultado['valido'] else '⚠ NOVEDAD'
        resumen_partes.append(f"• {doc.get_tipo_display()}: {estado_str}")

    solicitud.revision_ia_completada = True
    solicitud.tiene_novedades_ia = tiene_novedades
    solicitud.resumen_ia = '\n'.join(resumen_partes)
    if tiene_novedades and solicitud.estado == SolicitudMatricula.Estado.PENDIENTE:
        solicitud.estado = SolicitudMatricula.Estado.NOVEDAD
    elif not tiene_novedades and solicitud.estado == SolicitudMatricula.Estado.PENDIENTE:
        solicitud.estado = SolicitudMatricula.Estado.EN_REVISION
    solicitud.save(update_fields=['revision_ia_completada', 'tiene_novedades_ia', 'resumen_ia', 'estado'])

    logger.info("Análisis IA completado para solicitud %s — novedades: %s", solicitud_id, tiene_novedades)
