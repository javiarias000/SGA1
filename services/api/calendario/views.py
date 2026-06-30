import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from .models import EventoCalendario


@login_required
def calendario_view(request):
    try:
        usuario = request.user.usuario
    except Exception:
        usuario = None

    if request.method == 'POST' and request.user.is_staff:
        titulo = request.POST.get('titulo', '').strip()
        if titulo:
            EventoCalendario.objects.create(
                titulo=titulo,
                descripcion=request.POST.get('descripcion', ''),
                fecha_inicio=request.POST.get('fecha_inicio'),
                fecha_fin=request.POST.get('fecha_fin') or request.POST.get('fecha_inicio'),
                tipo=request.POST.get('tipo', 'EVENTO'),
                color=request.POST.get('color', '#4338ca'),
                visible_para=request.POST.get('visible_para', 'ALL'),
                creado_por=usuario,
            )
            messages.success(request, 'Evento creado.')
        return redirect('calendario:calendario')

    eventos = EventoCalendario.objects.all()
    if usuario:
        if usuario.rol == 'DOCENTE':
            eventos = eventos.exclude(visible_para='ESTUDIANTES')
        elif usuario.rol == 'ESTUDIANTE':
            eventos = eventos.exclude(visible_para='DOCENTES')

    eventos_json = [
        {
            'title': e.titulo,
            'start': str(e.fecha_inicio),
            'end': str(e.fecha_fin),
            'color': e.color,
            'extendedProps': {'tipo': e.get_tipo_display(), 'descripcion': e.descripcion},
        }
        for e in eventos
    ]
    return render(request, 'calendario/calendario.html', {
        'eventos_json': json.dumps(eventos_json),
        'tipos': EventoCalendario.Tipo.choices,
        'is_staff': request.user.is_staff,
        'proximos': eventos.filter(fecha_inicio__gte=__import__('datetime').date.today()).order_by('fecha_inicio')[:5],
    })


@login_required
def eliminar_evento_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, 'Sin permiso.')
        return redirect('calendario:calendario')
    e = get_object_or_404(EventoCalendario, pk=pk)
    e.delete()
    messages.success(request, 'Evento eliminado.')
    return redirect('calendario:calendario')


@login_required
@require_GET
def eventos_json_view(request):
    eventos = EventoCalendario.objects.all()
    data = [
        {'title': e.titulo, 'start': str(e.fecha_inicio), 'end': str(e.fecha_fin), 'color': e.color}
        for e in eventos
    ]
    return JsonResponse(data, safe=False)
