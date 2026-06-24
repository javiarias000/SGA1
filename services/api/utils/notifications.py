# ============================================
# SISTEMA DE NOTIFICACIONES
# Canales: Email  +  WhatsApp (Evolution API)
# Archivo: utils/notifications.py
# ============================================

import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from classes.models import CalificacionParcial
from utils.whatsapp import evolution

logger = logging.getLogger(__name__)

CONSERVATORIO = 'Conservatorio Bolívar de Ambato'
CICLO = '2025-2026'


# ──────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────

def _escala_para_nota(nota: float) -> dict:
    """Retorna la escala cualitativa sin necesitar una instancia de CalificacionParcial."""
    if nota >= 9:
        return {'codigo': 'DAR', 'nombre': 'Domina los Aprendizajes Requeridos'}
    elif nota >= 7:
        return {'codigo': 'AAR', 'nombre': 'Alcanza los Aprendizajes Requeridos'}
    elif nota > 4:
        return {'codigo': 'PAAR', 'nombre': 'Próximo a Alcanzar los Aprendizajes'}
    else:
        return {'codigo': 'NAAR', 'nombre': 'No Alcanza los Aprendizajes Requeridos'}


def _telefono_representante(student) -> str | None:
    """Obtiene el teléfono del representante o del estudiante (en ese orden)."""
    if student.parent_phone:
        return student.parent_phone
    if student.usuario and student.usuario.phone:
        return student.usuario.phone
    return None


def _email_representante(student) -> str | None:
    """Obtiene el email del representante o del estudiante."""
    if student.parent_email:
        return student.parent_email
    if student.usuario and student.usuario.email:
        return student.usuario.email
    return None


# ──────────────────────────────────────────────
# Canal: EMAIL
# ──────────────────────────────────────────────

class NotificacionEmail:
    """Notificaciones por correo electrónico."""

    @staticmethod
    def enviar_reporte_calificaciones(student, representante_email: str) -> bool:
        """Envía reporte de calificaciones al representante."""
        try:
            resumen = CalificacionParcial.obtener_resumen_estudiante(student)
            promedio = resumen['promedio_general']

            context = {
                'estudiante': student,
                'resumen': resumen,
                'promedio_general': promedio,
                'materias': resumen['materias'],
                'escala': _escala_para_nota(promedio) if promedio > 0 else None,
                'conservatorio': CONSERVATORIO,
                'anio_academico': CICLO,
            }

            html_content = render_to_string('emails/reporte_calificaciones.html', context)
            text_content = strip_tags(html_content)
            nombre = student.name

            msg = EmailMultiAlternatives(
                subject=f'Reporte de Calificaciones - {nombre}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[representante_email],
            )
            msg.attach_alternative(html_content, 'text/html')
            msg.send()
            logger.info(f'Email reporte calificaciones → {representante_email} ({nombre})')
            return True
        except Exception as exc:
            logger.error(f'Error enviando email reporte: {exc}')
            return False

    @staticmethod
    def enviar_alerta_bajo_rendimiento(student, representante_email: str, materia) -> bool:
        """Alerta cuando el estudiante tiene bajo rendimiento en una materia."""
        try:
            promedio = CalificacionParcial.calcular_promedio_quimestre(student, materia)

            context = {
                'estudiante': student,
                'materia': materia,
                'promedio': float(promedio),
                'escala': _escala_para_nota(float(promedio)),
                'conservatorio': CONSERVATORIO,
            }

            html_content = render_to_string('emails/alerta_rendimiento.html', context)
            text_content = strip_tags(html_content)
            nombre = student.name

            msg = EmailMultiAlternatives(
                subject=f'Alerta de Rendimiento - {nombre}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[representante_email],
            )
            msg.attach_alternative(html_content, 'text/html')
            msg.send()
            logger.info(f'Email alerta rendimiento → {representante_email} ({nombre})')
            return True
        except Exception as exc:
            logger.error(f'Error enviando alerta email: {exc}')
            return False

    @staticmethod
    def enviar_reporte_mensual_docente(teacher, mes: str) -> bool:
        """Envía reporte mensual al docente con estadísticas de sus estudiantes."""
        try:
            from students.models import Student
            from classes.models import Enrollment

            # Obtener estudiantes reales del docente via Enrollment
            usuario_ids = (
                Enrollment.objects
                .filter(docente=teacher.usuario, estado='ACTIVO')
                .values_list('estudiante_id', flat=True)
                .distinct()
            )
            estudiantes = Student.objects.filter(usuario_id__in=usuario_ids)

            estadisticas = {
                'total_estudiantes': estudiantes.count(),
                'promedios': [],
                'alertas': [],
            }
            for student in estudiantes:
                promedio = float(CalificacionParcial.calcular_promedio_general(student))
                estadisticas['promedios'].append({
                    'nombre': student.name,
                    'promedio': promedio,
                })
                if 0 < promedio < 7:
                    estadisticas['alertas'].append(student.name)

            # Email del docente desde auth_user
            email_destino = None
            if teacher.usuario and teacher.usuario.auth_user:
                email_destino = teacher.usuario.auth_user.email
            if not email_destino and teacher.usuario:
                email_destino = teacher.usuario.email
            if not email_destino:
                logger.warning(f'Docente {teacher} sin email — reporte mensual omitido')
                return False

            context = {
                'teacher': teacher,
                'mes': mes,
                'estadisticas': estadisticas,
                'conservatorio': CONSERVATORIO,
            }
            html_content = render_to_string('emails/reporte_docente.html', context)
            text_content = strip_tags(html_content)

            msg = EmailMultiAlternatives(
                subject=f'Reporte Mensual - {mes}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email_destino],
            )
            msg.attach_alternative(html_content, 'text/html')
            msg.send()
            logger.info(f'Email reporte mensual → {email_destino}')
            return True
        except Exception as exc:
            logger.error(f'Error enviando reporte mensual email: {exc}')
            return False


# ──────────────────────────────────────────────
# Canal: WHATSAPP (Evolution API)
# ──────────────────────────────────────────────

class NotificacionWhatsApp:
    """
    Notificaciones vía WhatsApp usando Evolution API.
    Misma interfaz de métodos que NotificacionEmail.
    Nunca lanza excepción — errores se loguean y retornan False.
    """

    # ── Plantillas de mensajes ──────────────────

    _TPL_REPORTE = (
        "📊 *Reporte de Calificaciones — {conservatorio}*\n\n"
        "Estimado/a representante de *{nombre}*:\n\n"
        "Promedio general: *{promedio}/10* ({escala})\n\n"
        "{detalle_materias}"
        "\nCiclo lectivo {ciclo}."
    )

    _TPL_ALERTA = (
        "⚠️ *Alerta de Rendimiento — {conservatorio}*\n\n"
        "El/La estudiante *{nombre}* tiene un promedio de *{promedio}/10* "
        "en la materia *{materia}* ({escala}).\n\n"
        "Por favor comuníquese con el docente para coordinar apoyo."
    )

    _TPL_REPORTE_DOCENTE = (
        "📈 *Reporte Mensual — {mes}*\n\n"
        "Estimado/a *{docente}*:\n\n"
        "Total estudiantes activos: *{total}*\n"
        "Estudiantes con promedio < 7: *{alertas}*\n\n"
        "{conservatorio} — {ciclo}"
    )

    _TPL_DEBER = (
        "📚 *Nuevo Deber — {conservatorio}*\n\n"
        "Materia: *{materia}*\n"
        "Título: *{titulo}*\n"
        "Fecha de entrega: *{fecha_entrega}*\n\n"
        "{descripcion}"
    )

    _TPL_CALIFICACION_DEBER = (
        "✅ *Tu deber fue calificado — {conservatorio}*\n\n"
        "Deber: *{titulo}*\n"
        "Calificación: *{calificacion}/{puntos_totales}*\n\n"
        "{retroalimentacion}"
    )

    # ── Métodos públicos ────────────────────────

    @staticmethod
    def enviar_reporte_calificaciones(student, telefono: str = None) -> bool:
        """
        Envía reporte de calificaciones al representante o al estudiante.
        Si no se pasa `telefono`, se resuelve automáticamente desde el perfil.
        """
        try:
            destino = telefono or _telefono_representante(student)
            if not destino:
                logger.warning(
                    f'WhatsApp reporte: {student.name} sin teléfono — omitido'
                )
                return False

            resumen = CalificacionParcial.obtener_resumen_estudiante(student)
            promedio = resumen['promedio_general']
            escala = _escala_para_nota(promedio)

            # Construir detalle por materia
            lineas = []
            for mat in resumen.get('materias', []):
                nombre_mat = getattr(mat.get('subject'), 'name', str(mat.get('subject', '')))
                nota_final = mat.get('nota_final', 0)
                lineas.append(f"  • {nombre_mat}: {nota_final}/10")
            detalle = '\n'.join(lineas) + '\n' if lineas else ''

            texto = NotificacionWhatsApp._TPL_REPORTE.format(
                conservatorio=CONSERVATORIO,
                nombre=student.name,
                promedio=round(promedio, 2),
                escala=escala['codigo'],
                detalle_materias=detalle,
                ciclo=CICLO,
            )
            return evolution.send_text(destino, texto)
        except Exception as exc:
            logger.error(f'WhatsApp reporte calificaciones error: {exc}')
            return False

    @staticmethod
    def enviar_alerta_bajo_rendimiento(student, materia, telefono: str = None) -> bool:
        """
        Alerta al representante cuando el promedio en una materia es < 7.
        Si no se pasa `telefono`, se resuelve automáticamente.
        """
        try:
            destino = telefono or _telefono_representante(student)
            if not destino:
                logger.warning(
                    f'WhatsApp alerta: {student.name} sin teléfono — omitido'
                )
                return False

            promedio = float(CalificacionParcial.calcular_promedio_quimestre(student, materia))
            escala = _escala_para_nota(promedio)
            nombre_materia = getattr(materia, 'name', str(materia))

            texto = NotificacionWhatsApp._TPL_ALERTA.format(
                conservatorio=CONSERVATORIO,
                nombre=student.name,
                promedio=round(promedio, 2),
                materia=nombre_materia,
                escala=escala['codigo'],
            )
            return evolution.send_text(destino, texto)
        except Exception as exc:
            logger.error(f'WhatsApp alerta bajo rendimiento error: {exc}')
            return False

    @staticmethod
    def enviar_reporte_mensual_docente(teacher, mes: str) -> bool:
        """Envía resumen mensual al docente vía WhatsApp."""
        try:
            telefono = teacher.usuario.phone if teacher.usuario else None
            if not telefono:
                logger.warning(
                    f'WhatsApp reporte docente: {teacher} sin teléfono — omitido'
                )
                return False

            from students.models import Student
            from classes.models import Enrollment

            usuario_ids = (
                Enrollment.objects
                .filter(docente=teacher.usuario, estado='ACTIVO')
                .values_list('estudiante_id', flat=True)
                .distinct()
            )
            estudiantes = Student.objects.filter(usuario_id__in=usuario_ids)
            total = estudiantes.count()
            alertas = sum(
                1 for s in estudiantes
                if 0 < float(CalificacionParcial.calcular_promedio_general(s)) < 7
            )

            texto = NotificacionWhatsApp._TPL_REPORTE_DOCENTE.format(
                mes=mes,
                docente=teacher.usuario.nombre,
                total=total,
                alertas=alertas,
                conservatorio=CONSERVATORIO,
                ciclo=CICLO,
            )
            return evolution.send_text(telefono, texto)
        except Exception as exc:
            logger.error(f'WhatsApp reporte mensual docente error: {exc}')
            return False

    @staticmethod
    def notificar_deber_asignado(deber) -> int:
        """
        Notifica a todos los estudiantes inscritos en la clase del deber.
        Retorna el número de mensajes enviados exitosamente.
        """
        try:
            from classes.models import Enrollment
            from students.models import Student

            enviados = 0
            nombre_materia = (
                deber.clase.subject.name
                if deber.clase and deber.clase.subject
                else 'Materia'
            )
            fecha_str = deber.fecha_entrega.strftime('%d/%m/%Y %H:%M')
            descripcion = deber.descripcion[:200] if deber.descripcion else ''

            # Obtener estudiantes del grupo
            enrollments = Enrollment.objects.filter(
                clase=deber.clase, estado='ACTIVO'
            ).select_related('estudiante')

            for enr in enrollments:
                usuario = enr.estudiante
                if not usuario:
                    continue
                # Buscar teléfono del estudiante
                telefono = usuario.phone
                if not telefono:
                    try:
                        telefono = usuario.student_profile.parent_phone
                    except Exception:
                        pass
                if not telefono:
                    continue

                texto = NotificacionWhatsApp._TPL_DEBER.format(
                    conservatorio=CONSERVATORIO,
                    materia=nombre_materia,
                    titulo=deber.titulo,
                    fecha_entrega=fecha_str,
                    descripcion=descripcion,
                )
                if evolution.send_text(telefono, texto):
                    enviados += 1

            logger.info(
                f'WhatsApp deber "{deber.titulo}": {enviados} mensajes enviados'
            )
            return enviados
        except Exception as exc:
            logger.error(f'WhatsApp notificar_deber_asignado error: {exc}')
            return 0

    @staticmethod
    def notificar_calificacion_deber(entrega) -> bool:
        """Notifica al estudiante que su deber fue calificado."""
        try:
            usuario = entrega.estudiante
            telefono = usuario.phone if usuario else None
            if not telefono:
                try:
                    telefono = usuario.student_profile.parent_phone
                except Exception:
                    pass
            if not telefono:
                logger.warning(
                    f'WhatsApp calificacion deber: {usuario} sin teléfono — omitido'
                )
                return False

            retroalimentacion = (
                f'Comentario del docente: {entrega.retroalimentacion}'
                if entrega.retroalimentacion
                else ''
            )

            texto = NotificacionWhatsApp._TPL_CALIFICACION_DEBER.format(
                conservatorio=CONSERVATORIO,
                titulo=entrega.deber.titulo,
                calificacion=entrega.calificacion,
                puntos_totales=entrega.deber.puntos_totales,
                retroalimentacion=retroalimentacion,
            )
            return evolution.send_text(telefono, texto)
        except Exception as exc:
            logger.error(f'WhatsApp notificar_calificacion_deber error: {exc}')
            return False
