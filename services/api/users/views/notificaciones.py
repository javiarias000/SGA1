from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from users.models import Notificacion


@login_required
def notificaciones_view(request):
    try:
        usuario = request.user.usuario
    except Exception:
        return render(request, 'users/notificaciones.html', {'notificaciones': []})
    notificaciones = Notificacion.objects.filter(usuario=usuario).order_by('-fecha')[:50]
    Notificacion.objects.filter(usuario=usuario, leida=False).update(leida=True)
    return render(request, 'users/notificaciones.html', {'notificaciones': notificaciones})


@login_required
@require_POST
def marcar_leida_view(request, pk):
    try:
        usuario = request.user.usuario
    except Exception:
        return JsonResponse({'ok': False}, status=403)
    n = get_object_or_404(Notificacion, pk=pk, usuario=usuario)
    n.leida = True
    n.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def marcar_todas_leidas_view(request):
    try:
        usuario = request.user.usuario
    except Exception:
        return JsonResponse({'ok': False}, status=403)
    Notificacion.objects.filter(usuario=usuario, leida=False).update(leida=True)
    return JsonResponse({'ok': True})
