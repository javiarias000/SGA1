import logging

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from academia.models import Horario
from academia.serializers import HorarioSerializer
from students.models import Student
from teachers.models import Teacher
from utils.notifications import NotificacionWhatsApp
from utils.whatsapp import evolution

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# ViewSet existente (sin cambios)
# ──────────────────────────────────────────────

class HorarioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Horario.objects.all().select_related('curso', 'docente', 'clase')
    serializer_class = HorarioSerializer


# ──────────────────────────────────────────────
# Endpoints de notificaciones WhatsApp
# ──────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_reporte_calificaciones(request):
    """
    Envía el reporte de calificaciones de un estudiante vía WhatsApp.

    Body:
        {
            "estudiante_id": 42,
            "telefono": "0991234567"   ← opcional; si se omite se usa el del perfil
        }

    Respuesta:
        200  {"ok": true,  "mensaje": "Reporte enviado a 0991234567"}
        400  {"ok": false, "error": "..."}
        404  {"ok": false, "error": "Estudiante no encontrado"}
    """
    estudiante_id = request.data.get('estudiante_id')
    telefono = request.data.get('telefono')

    if not estudiante_id:
        return Response(
            {'ok': False, 'error': 'Falta estudiante_id'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        student = Student.objects.select_related('usuario').get(pk=estudiante_id)
    except Student.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Estudiante no encontrado'},
            status=status.HTTP_404_NOT_FOUND,
        )

    ok = NotificacionWhatsApp.enviar_reporte_calificaciones(student, telefono)
    if ok:
        destino = telefono or student.parent_phone or (student.usuario.phone if student.usuario else 'N/A')
        return Response({'ok': True, 'mensaje': f'Reporte enviado a {destino}'})
    return Response(
        {'ok': False, 'error': 'No se pudo enviar el mensaje. Revisa logs para detalles.'},
        status=status.HTTP_502_BAD_GATEWAY,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_alerta_rendimiento(request):
    """
    Envía una alerta de bajo rendimiento para un estudiante en una materia.

    Body:
        {
            "estudiante_id": 42,
            "materia_id": 7,
            "telefono": "0991234567"   ← opcional
        }
    """
    from subjects.models import Subject

    estudiante_id = request.data.get('estudiante_id')
    materia_id = request.data.get('materia_id')
    telefono = request.data.get('telefono')

    if not estudiante_id or not materia_id:
        return Response(
            {'ok': False, 'error': 'Faltan estudiante_id y/o materia_id'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        student = Student.objects.select_related('usuario').get(pk=estudiante_id)
    except Student.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Estudiante no encontrado'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        materia = Subject.objects.get(pk=materia_id)
    except Subject.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Materia no encontrada'},
            status=status.HTTP_404_NOT_FOUND,
        )

    ok = NotificacionWhatsApp.enviar_alerta_bajo_rendimiento(student, materia, telefono)
    if ok:
        return Response({'ok': True, 'mensaje': 'Alerta enviada'})
    return Response(
        {'ok': False, 'error': 'No se pudo enviar la alerta. Revisa logs.'},
        status=status.HTTP_502_BAD_GATEWAY,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_reporte_docente(request):
    """
    Envía reporte mensual a un docente vía WhatsApp.

    Body:
        {
            "teacher_id": 3,
            "mes": "Abril 2026"
        }
    """
    teacher_id = request.data.get('teacher_id')
    mes = request.data.get('mes', 'Mes actual')

    if not teacher_id:
        return Response(
            {'ok': False, 'error': 'Falta teacher_id'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        teacher = Teacher.objects.select_related('usuario').get(pk=teacher_id)
    except Teacher.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Docente no encontrado'},
            status=status.HTTP_404_NOT_FOUND,
        )

    ok = NotificacionWhatsApp.enviar_reporte_mensual_docente(teacher, mes)
    if ok:
        return Response({'ok': True, 'mensaje': f'Reporte mensual enviado al docente {teacher}'})
    return Response(
        {'ok': False, 'error': 'No se pudo enviar. Verifica que el docente tenga teléfono registrado.'},
        status=status.HTTP_502_BAD_GATEWAY,
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def test_whatsapp(request):
    """
    Endpoint de prueba — solo admin.
    Verifica conexión con Evolution API y opcionalmente envía un mensaje de prueba.

    Body (todos opcionales):
        {
            "telefono": "0991234567",   ← si se incluye, envía mensaje de prueba
            "mensaje": "Hola desde el conservatorio"
        }
    """
    estado = evolution.verificar_conexion()
    resultado = {'conexion': estado}

    telefono = request.data.get('telefono')
    if telefono:
        mensaje = request.data.get('mensaje', f'Prueba desde {evolution.instance} ✓')
        ok = evolution.send_text(telefono, mensaje)
        resultado['mensaje_enviado'] = ok
        resultado['destino'] = telefono

    return Response(resultado)
