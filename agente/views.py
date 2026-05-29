import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q

from .models import AlertaEstudiante, InformeAsistido, ConfiguracionAgente


def _es_docente_o_staff(user):
    try:
        return user.is_staff or user.is_superuser or user.usuario_profile.rol == 'DOCENTE'
    except Exception:
        return user.is_staff or user.is_superuser


# ─── PANEL DE ALERTAS ────────────────────────────────────────────────────────

@login_required
def panel_alertas(request):
    if not _es_docente_o_staff(request.user):
        messages.error(request, 'No tienes acceso a este panel.')
        return redirect('/')

    # Filtros
    severidad = request.GET.get('severidad', '')
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '')

    alertas = AlertaEstudiante.objects.select_related(
        'estudiante__usuario', 'materia'
    ).all()

    # Docentes solo ven alertas de sus estudiantes
    try:
        usuario = request.user.usuario_profile
        if usuario.rol == 'DOCENTE' and not request.user.is_staff:
            from classes.models import Enrollment
            mis_estudiantes = Enrollment.objects.filter(
                docente=usuario, estado='ACTIVO'
            ).values_list('estudiante_id', flat=True)
            alertas = alertas.filter(estudiante__usuario__in=mis_estudiantes)
    except Exception:
        pass

    if severidad:
        alertas = alertas.filter(severidad=severidad)
    if tipo:
        alertas = alertas.filter(tipo=tipo)
    if estado:
        alertas = alertas.filter(estado=estado)
    if q:
        alertas = alertas.filter(estudiante__usuario__nombre__icontains=q)

    stats = {
        'total': alertas.count(),
        'criticas': alertas.filter(severidad='CRITICA').count(),
        'nuevas': alertas.filter(estado='NUEVA').count(),
        'resueltas': alertas.filter(estado='RESUELTA').count(),
    }

    return render(request, 'agente/panel_alertas.html', {
        'alertas': alertas[:100],
        'stats': stats,
        'severidades': AlertaEstudiante.Severidad.choices,
        'tipos': AlertaEstudiante.TipoAlerta.choices,
        'estados': AlertaEstudiante.Estado.choices,
        'filtros': {'severidad': severidad, 'tipo': tipo, 'estado': estado, 'q': q},
    })


@login_required
def detalle_alerta(request, pk):
    if not _es_docente_o_staff(request.user):
        return redirect('/')

    alerta = get_object_or_404(
        AlertaEstudiante.objects.select_related('estudiante__usuario', 'materia'), pk=pk
    )

    if alerta.estado == AlertaEstudiante.Estado.NUEVA:
        alerta.estado = AlertaEstudiante.Estado.VISTA
        alerta.save(update_fields=['estado'])

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(AlertaEstudiante.Estado.choices):
            alerta.estado = nuevo_estado
            alerta.save(update_fields=['estado'])
            messages.success(request, 'Estado actualizado.')
            return redirect('agente:panel_alertas')

    return render(request, 'agente/detalle_alerta.html', {'alerta': alerta})


# ─── ANÁLISIS MANUAL ─────────────────────────────────────────────────────────

@login_required
@require_POST
def analizar_estudiante_ajax(request, student_id):
    if not _es_docente_o_staff(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    try:
        from .tasks import analizar_estudiante
        analizar_estudiante.delay(student_id)
        return JsonResponse({'ok': True, 'mensaje': 'Análisis encolado correctamente.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def lanzar_analisis_completo(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Solo el administrador puede lanzar el análisis completo.')
        return redirect('agente:panel_alertas')
    try:
        from .tasks import analizar_rendimiento_semanal
        analizar_rendimiento_semanal.delay()
        messages.success(request, 'Análisis completo encolado. Los resultados aparecerán en minutos.')
    except Exception as e:
        messages.error(request, f'Error al lanzar análisis: {e}')
    return redirect('agente:panel_alertas')


# ─── ASISTENTE DE INFORMES ───────────────────────────────────────────────────

@login_required
def asistente_informe(request):
    """Interfaz para que el docente pegue un informe y reciba la versión mejorada."""
    if not _es_docente_o_staff(request.user):
        return redirect('/')

    informe_mejorado = None

    if request.method == 'POST':
        texto = request.POST.get('texto_original', '').strip()
        activity_id = request.POST.get('activity_id') or None

        if not texto:
            messages.error(request, 'El texto del informe no puede estar vacío.')
        elif len(texto) < 20:
            messages.error(request, 'El texto es demasiado corto para analizar.')
        else:
            try:
                usuario = request.user.usuario_profile
                docente_id = usuario.pk
            except Exception:
                messages.error(request, 'No se pudo identificar tu perfil de docente.')
                return render(request, 'agente/asistente_informe.html', {})

            # Ejecución síncrona para mostrar resultado inmediato
            from .tasks import mejorar_informe_docente
            result_id = mejorar_informe_docente(
                texto_original=texto,
                docente_id=docente_id,
                activity_id=int(activity_id) if activity_id else None,
            )
            if result_id:
                informe_mejorado = InformeAsistido.objects.get(pk=result_id)
            else:
                messages.error(request, 'No se pudo procesar el informe. Verifica la API key de OpenAI.')

    # Historial reciente del docente
    try:
        historial = InformeAsistido.objects.filter(
            docente=request.user.usuario_profile
        ).order_by('-created_at')[:10]
    except Exception:
        historial = []

    return render(request, 'agente/asistente_informe.html', {
        'informe_mejorado': informe_mejorado,
        'historial': historial,
    })


@login_required
@require_POST
def aceptar_informe(request, pk):
    """El docente acepta o rechaza el informe mejorado."""
    if not _es_docente_o_staff(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    informe = get_object_or_404(InformeAsistido, pk=pk)
    accion = request.POST.get('accion')  # 'aceptar' | 'rechazar'

    if accion == 'aceptar':
        informe.estado = InformeAsistido.Estado.ACEPTADO
        # Si hay Activity vinculada, actualiza el campo observations
        if informe.activity:
            informe.activity.observations = informe.texto_mejorado
            informe.activity.save(update_fields=['observations'])
        informe.save(update_fields=['estado'])
        return JsonResponse({'ok': True, 'mensaje': 'Informe aplicado al registro de clase.'})
    elif accion == 'rechazar':
        informe.estado = InformeAsistido.Estado.RECHAZADO
        informe.save(update_fields=['estado'])
        return JsonResponse({'ok': True, 'mensaje': 'Informe rechazado.'})

    return JsonResponse({'error': 'Acción no válida'}, status=400)


# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────

@login_required
def configuracion_agente(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('agente:panel_alertas')

    config = ConfiguracionAgente.get()

    if request.method == 'POST':
        try:
            config.umbral_nota_alerta = float(request.POST.get('umbral_nota_alerta', 6))
            config.umbral_inasistencia_pct = float(request.POST.get('umbral_inasistencia_pct', 20))
            config.analisis_activo = 'analisis_activo' in request.POST
            config.notificar_docentes = 'notificar_docentes' in request.POST
            config.notificar_representantes = 'notificar_representantes' in request.POST
            config.ciclo_lectivo_activo = request.POST.get('ciclo_lectivo_activo', '')
            config.save()
            messages.success(request, 'Configuración guardada.')
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')
        return redirect('agente:configuracion')

    return render(request, 'agente/configuracion.html', {'config': config})
