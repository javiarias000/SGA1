# ============================================
# SISTEMA DE NOTIFICACIONES POR EMAIL
# Archivo: utils/notifications.py
# ============================================

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from classes.models import CalificacionParcial
import logging

logger = logging.getLogger(__name__)


class NotificacionEmail:
    """Clase para gestionar notificaciones por email"""
    
    @staticmethod
    def enviar_reporte_calificaciones(estudiante, representante_email):
        """
        Envía reporte de calificaciones al representante
        """
        try:
            # Obtener resumen del estudiante
            resumen = CalificacionParcial.obtener_resumen_estudiante(estudiante)
            
            # Contexto para el template
            context = {
                'estudiante': estudiante,
                'resumen': resumen,
                'promedio_general': resumen['promedio_general'],
                'materias': resumen['materias'],
                'escala': CalificacionParcial().get_escala_cualitativa() if resumen['promedio_general'] > 0 else None,
                'conservatorio': 'Conservatorio Bolívar de Ambato',
                'anio_academico': '2025-2026'
            }
            
            # Renderizar template HTML
            html_content = render_to_string('emails/reporte_calificaciones.html', context)
            text_content = strip_tags(html_content)
            
            # Crear email
            subject = f'📊 Reporte de Calificaciones - {estudiante.name}'
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[representante_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar
            email.send()
            logger.info(f'Email enviado a {representante_email} para {estudiante.name}')
            return True
            
        except Exception as e:
            logger.error(f'Error enviando email: {str(e)}')
            return False
    
    @staticmethod
    def enviar_alerta_bajo_rendimiento(estudiante, representante_email, materia):
        """
        Alerta cuando el estudiante tiene bajo rendimiento en una materia
        """
        try:
            promedio_materia = CalificacionParcial.calcular_promedio_quimestre(
                estudiante, materia
            )
            
            context = {
                'estudiante': estudiante,
                'materia': materia,
                'promedio': promedio_materia,
                'escala': CalificacionParcial().get_escala_cualitativa(),
                'conservatorio': 'Conservatorio Bolívar de Ambato'
            }
            
            html_content = render_to_string('emails/alerta_rendimiento.html', context)
            text_content = strip_tags(html_content)
            
            subject = f'⚠️ Alerta de Rendimiento - {estudiante.name}'
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[representante_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            return True
        except Exception as e:
            logger.error(f'Error enviando alerta: {str(e)}')
            return False
    
    @staticmethod
    def enviar_reporte_mensual_docente(teacher, mes):
        """
        Envía reporte mensual al docente con estadísticas de sus estudiantes
        """
        try:
            from students.models import Student
            
            estudiantes = Student.objects.filter(teacher=teacher, active=True)
            
            estadisticas = {
                'total_estudiantes': estudiantes.count(),
                'promedios': [],
                'alertas': []
            }
            
            for estudiante in estudiantes:
                promedio = CalificacionParcial.calcular_promedio_general(estudiante)
                estadisticas['promedios'].append({
                    'nombre': estudiante.name,
                    'promedio': promedio
                })
                
                if 0 < promedio < 7:
                    estadisticas['alertas'].append(estudiante.name)
            
            context = {
                'teacher': teacher,
                'mes': mes,
                'estadisticas': estadisticas,
                'conservatorio': 'Conservatorio Bolívar de Ambato'
            }
            
            html_content = render_to_string('emails/reporte_docente.html', context)
            text_content = strip_tags(html_content)
            
            subject = f'📈 Reporte Mensual - {mes}'
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[teacher.user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            return True
        except Exception as e:
            logger.error(f'Error enviando reporte docente: {str(e)}')
            return False


