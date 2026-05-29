"""
Agente IA Académico — Tareas Celery

Tareas disponibles:
  - analizar_rendimiento_semanal(): escaneo completo, programada semanalmente
  - analizar_estudiante(student_id): análisis individual bajo demanda
  - mejorar_informe_docente(texto, activity_id, docente_id): mejora de texto
  - enviar_notificaciones_pendientes(): envío de emails acumulados
"""
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import date

logger = logging.getLogger(__name__)


# ─── UTILIDADES ─────────────────────────────────────────────────────────────

def _get_openai_client():
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        raise ValueError('OPENAI_API_KEY no configurada')
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _ciclo_actual():
    today = date.today()
    return f"{today.year}-{today.year + 1}"


def _calcular_porcentaje_inasistencia(student):
    """Retorna (total_clases, ausencias, porcentaje) para el ciclo activo."""
    from classes.models import Asistencia, Enrollment
    enrollments = Enrollment.objects.filter(estudiante=student.usuario, estado='ACTIVO')
    total = Asistencia.objects.filter(inscripcion__in=enrollments).count()
    ausencias = Asistencia.objects.filter(
        inscripcion__in=enrollments,
        estado='Ausente'
    ).count()
    pct = (ausencias / total * 100) if total > 0 else 0
    return total, ausencias, round(pct, 2)


def _obtener_promedios_por_materia(student):
    """Retorna lista de {materia, promedio, nivel} ordenada por promedio asc."""
    from classes.models import CalificacionParcial
    from subjects.models import Subject
    from django.db.models import Avg

    materias = (
        CalificacionParcial.objects
        .filter(student=student)
        .values('subject__id', 'subject__name')
        .annotate(promedio=Avg('calificacion'))
        .order_by('promedio')
    )

    def nivel(p):
        if p is None:
            return 'Sin datos'
        if p >= 9:
            return 'DAR'
        if p >= 7:
            return 'AAR'
        if p > 4:
            return 'PAAR'
        return 'NAAR'

    return [
        {
            'subject_id': m['subject__id'],
            'materia': m['subject__name'],
            'promedio': round(float(m['promedio']), 2) if m['promedio'] else None,
            'nivel': nivel(m['promedio']),
        }
        for m in materias
    ]


# ─── ANÁLISIS INDIVIDUAL ─────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=2)
def analizar_estudiante(self, student_id: int):
    """Analiza el rendimiento de un estudiante específico y genera alertas si necesario."""
    from students.models import Student
    from agente.models import AlertaEstudiante, ConfiguracionAgente

    try:
        student = Student.objects.select_related('usuario').get(pk=student_id)
    except Student.DoesNotExist:
        logger.warning(f'analizar_estudiante: student {student_id} no encontrado')
        return

    config = ConfiguracionAgente.get()
    if not config.analisis_activo:
        return

    ciclo = config.ciclo_lectivo_activo or _ciclo_actual()
    promedios = _obtener_promedios_por_materia(student)
    total_clases, ausencias, pct_inasistencia = _calcular_porcentaje_inasistencia(student)

    alertas_generadas = []

    # ── 1. Materias con nota baja ────────────────────────────────────────────
    materias_bajas = [
        m for m in promedios
        if m['promedio'] is not None and m['promedio'] < float(config.umbral_nota_alerta)
    ]

    if len(materias_bajas) >= 3:
        alerta = _crear_alerta_multiples_materias(student, materias_bajas, pct_inasistencia, ciclo)
        alertas_generadas.append(alerta)
    else:
        for m in materias_bajas:
            alerta = _crear_alerta_nota_baja(student, m, pct_inasistencia, ciclo)
            alertas_generadas.append(alerta)

    # ── 2. Alta inasistencia ─────────────────────────────────────────────────
    if pct_inasistencia >= float(config.umbral_inasistencia_pct):
        alerta = _crear_alerta_inasistencia(student, total_clases, ausencias, pct_inasistencia, ciclo)
        alertas_generadas.append(alerta)

    logger.info(
        f'analizar_estudiante: {student} → {len(alertas_generadas)} alertas generadas'
    )
    return len(alertas_generadas)


def _contexto_estudiante_texto(student, materias_bajas, pct_inasistencia):
    nombre = student.usuario.nombre
    lineas = [f'Estudiante: {nombre}']
    if student.usuario.rol:
        lineas.append(f'Rol: {student.usuario.rol}')

    if materias_bajas:
        lineas.append('Materias con bajo rendimiento:')
        for m in materias_bajas:
            lineas.append(f'  - {m["materia"]}: {m["promedio"]} ({m["nivel"]})')

    if pct_inasistencia > 0:
        lineas.append(f'Porcentaje de inasistencia: {pct_inasistencia}%')

    return '\n'.join(lineas)


def _llamar_agente(prompt_sistema: str, prompt_usuario: str) -> dict:
    """Llama a GPT-4o y retorna {analisis, recomendaciones, mensaje_docente, mensaje_representante}."""
    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': prompt_sistema},
                {'role': 'user', 'content': prompt_usuario},
            ],
            response_format={'type': 'json_object'},
            temperature=0.4,
            max_tokens=1500,
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f'_llamar_agente error: {e}')
        return {
            'analisis': 'Análisis no disponible (error de IA).',
            'recomendaciones': '',
            'mensaje_docente': '',
            'mensaje_representante': '',
        }


SISTEMA_ALERTAS = """
Eres un agente educativo especializado en el seguimiento académico de estudiantes de un
conservatorio de música. Analizas datos de rendimiento y redactas comunicados en español
formal pero empático, dirigidos a docentes y representantes legales.

Responde SIEMPRE en JSON con las claves:
  analisis           (str) — análisis objetivo de la situación en 2-3 párrafos
  recomendaciones    (str) — 3-5 acciones concretas para el docente, en lista
  mensaje_docente    (str) — comunicado formal para el docente, máx 150 palabras
  mensaje_representante (str) — comunicado para el representante/padre, máx 150 palabras,
                               en tono empático sin alarmar innecesariamente
"""


def _crear_alerta_nota_baja(student, materia_data, pct_inasistencia, ciclo):
    from agente.models import AlertaEstudiante

    contexto = _contexto_estudiante_texto(student, [materia_data], pct_inasistencia)
    promedio = materia_data['promedio']
    nivel = materia_data['nivel']

    severidad = (
        AlertaEstudiante.Severidad.CRITICA if promedio <= 4
        else AlertaEstudiante.Severidad.ALTA if promedio <= 5
        else AlertaEstudiante.Severidad.MEDIA
    )

    resultado = _llamar_agente(
        SISTEMA_ALERTAS,
        f'El siguiente estudiante presenta calificación baja ({nivel}) en la materia '
        f'"{materia_data["materia"]}" con promedio {promedio}.\n\n{contexto}',
    )

    from subjects.models import Subject
    try:
        materia_obj = Subject.objects.get(pk=materia_data['subject_id'])
    except Subject.DoesNotExist:
        materia_obj = None

    return AlertaEstudiante.objects.create(
        estudiante=student,
        tipo=AlertaEstudiante.TipoAlerta.CALIFICACION_BAJA,
        severidad=severidad,
        materia=materia_obj,
        promedio_detectado=promedio,
        porcentaje_inasistencia=pct_inasistencia,
        analisis_ia=resultado.get('analisis', ''),
        recomendaciones_ia=resultado.get('recomendaciones', ''),
        mensaje_docente=resultado.get('mensaje_docente', ''),
        mensaje_representante=resultado.get('mensaje_representante', ''),
        ciclo_lectivo=ciclo,
    )


def _crear_alerta_multiples_materias(student, materias_bajas, pct_inasistencia, ciclo):
    from agente.models import AlertaEstudiante

    contexto = _contexto_estudiante_texto(student, materias_bajas, pct_inasistencia)
    promedio_general = round(
        sum(m['promedio'] for m in materias_bajas if m['promedio']) / len(materias_bajas), 2
    )

    resultado = _llamar_agente(
        SISTEMA_ALERTAS,
        f'El estudiante presenta bajo rendimiento en {len(materias_bajas)} materias simultáneamente. '
        f'Promedio general afectado: {promedio_general}.\n\n{contexto}',
    )

    return AlertaEstudiante.objects.create(
        estudiante=student,
        tipo=AlertaEstudiante.TipoAlerta.MULTIPLES_MATERIAS,
        severidad=AlertaEstudiante.Severidad.CRITICA,
        promedio_detectado=promedio_general,
        porcentaje_inasistencia=pct_inasistencia,
        analisis_ia=resultado.get('analisis', ''),
        recomendaciones_ia=resultado.get('recomendaciones', ''),
        mensaje_docente=resultado.get('mensaje_docente', ''),
        mensaje_representante=resultado.get('mensaje_representante', ''),
        ciclo_lectivo=ciclo,
    )


def _crear_alerta_inasistencia(student, total, ausencias, pct, ciclo):
    from agente.models import AlertaEstudiante

    contexto = _contexto_estudiante_texto(student, [], pct)
    severidad = (
        AlertaEstudiante.Severidad.CRITICA if pct >= 35
        else AlertaEstudiante.Severidad.ALTA if pct >= 25
        else AlertaEstudiante.Severidad.MEDIA
    )

    resultado = _llamar_agente(
        SISTEMA_ALERTAS,
        f'El estudiante tiene {ausencias} ausencias de {total} clases ({pct}% de inasistencia). '
        f'Esto supera el umbral permitido por el reglamento del conservatorio.\n\n{contexto}',
    )

    return AlertaEstudiante.objects.create(
        estudiante=student,
        tipo=AlertaEstudiante.TipoAlerta.INASISTENCIA,
        severidad=severidad,
        porcentaje_inasistencia=pct,
        analisis_ia=resultado.get('analisis', ''),
        recomendaciones_ia=resultado.get('recomendaciones', ''),
        mensaje_docente=resultado.get('mensaje_docente', ''),
        mensaje_representante=resultado.get('mensaje_representante', ''),
        ciclo_lectivo=ciclo,
    )


# ─── ANÁLISIS SEMANAL MASIVO ─────────────────────────────────────────────────

@shared_task
def analizar_rendimiento_semanal():
    """
    Tarea periódica: analiza todos los estudiantes activos.
    Encola una tarea individual por estudiante.
    """
    from students.models import Student
    from agente.models import ConfiguracionAgente

    config = ConfiguracionAgente.get()
    if not config.analisis_activo:
        logger.info('analizar_rendimiento_semanal: agente desactivado')
        return

    estudiantes = Student.objects.select_related('usuario').all()
    total = 0
    for student in estudiantes:
        analizar_estudiante.delay(student.pk)
        total += 1

    logger.info(f'analizar_rendimiento_semanal: {total} estudiantes encolados')
    return total


# ─── MEJORAR INFORME DE DOCENTE ──────────────────────────────────────────────

@shared_task(bind=True, max_retries=2)
def mejorar_informe_docente(self, texto_original: str, docente_id: int, activity_id: int = None):
    """
    Mejora el texto de un informe de clase escrito por un docente.
    Retorna el id del InformeAsistido creado.
    """
    from agente.models import InformeAsistido
    from users.models import Usuario

    try:
        docente = Usuario.objects.get(pk=docente_id)
    except Usuario.DoesNotExist:
        logger.warning(f'mejorar_informe_docente: docente {docente_id} no encontrado')
        return None

    activity = None
    if activity_id:
        try:
            from classes.models import Activity
            activity = Activity.objects.get(pk=activity_id)
        except Exception:
            pass

    sistema = """
Eres un asistente pedagógico especializado en conservatorios de música.
Tu tarea es mejorar los informes de clase escritos por docentes, corrigiendo ortografía,
gramática, estructura y claridad sin cambiar el contenido sustancial.

Responde en JSON con las claves:
  texto_mejorado  (str) — el informe corregido y mejorado
  sugerencias     (str) — lista breve de los cambios realizados y por qué
"""

    try:
        resultado = _llamar_agente(
            sistema,
            f'Mejora el siguiente informe de clase:\n\n"""\n{texto_original}\n"""',
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)

    informe = InformeAsistido.objects.create(
        activity=activity,
        docente=docente,
        texto_original=texto_original,
        texto_mejorado=resultado.get('texto_mejorado', texto_original),
        sugerencias_ia=resultado.get('sugerencias', ''),
    )

    logger.info(f'mejorar_informe_docente: InformeAsistido {informe.pk} creado')
    return informe.pk


# ─── ENVÍO DE NOTIFICACIONES ─────────────────────────────────────────────────

@shared_task
def enviar_notificaciones_pendientes():
    """
    Envía emails para todas las alertas que aún no fueron notificadas.
    Se ejecuta diariamente.
    """
    from agente.models import AlertaEstudiante, ConfiguracionAgente
    from django.core.mail import send_mail
    from django.conf import settings

    config = ConfiguracionAgente.get()
    pendientes = AlertaEstudiante.objects.filter(
        estado=AlertaEstudiante.Estado.NUEVA
    ).select_related('estudiante__usuario', 'materia')

    enviados = 0
    for alerta in pendientes:
        student = alerta.estudiante
        usuario = student.usuario

        # Email al docente
        if config.notificar_docentes and alerta.mensaje_docente:
            try:
                from classes.models import Enrollment
                docentes_emails = list(
                    Enrollment.objects
                    .filter(estudiante=usuario, estado='ACTIVO')
                    .exclude(docente=None)
                    .values_list('docente__email', flat=True)
                    .distinct()
                )
                if docentes_emails:
                    send_mail(
                        subject=f'[Alerta Académica] {usuario.nombre} — {alerta.get_tipo_display()}',
                        message=alerta.mensaje_docente,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@conservatorio.edu.ec'),
                        recipient_list=docentes_emails,
                        fail_silently=True,
                    )
                    alerta.email_docente_enviado = True
                    enviados += 1
            except Exception as e:
                logger.error(f'Error enviando email docente para alerta {alerta.pk}: {e}')

        # Email al representante
        if config.notificar_representantes and alerta.mensaje_representante:
            try:
                representante_email = getattr(student, 'parent_email', None)
                if representante_email:
                    send_mail(
                        subject=f'Seguimiento académico de {usuario.nombre}',
                        message=alerta.mensaje_representante,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@conservatorio.edu.ec'),
                        recipient_list=[representante_email],
                        fail_silently=True,
                    )
                    alerta.email_representante_enviado = True
                    alerta.estado = AlertaEstudiante.Estado.NOTIFICADA
                    enviados += 1
            except Exception as e:
                logger.error(f'Error enviando email representante para alerta {alerta.pk}: {e}')

        alerta.fecha_notificacion = timezone.now()
        alerta.save(update_fields=[
            'email_docente_enviado', 'email_representante_enviado',
            'estado', 'fecha_notificacion'
        ])

    logger.info(f'enviar_notificaciones_pendientes: {enviados} emails enviados')
    return enviados
