from .models import Notificacion


def notificaciones(request):
    if not request.user.is_authenticated:
        return {'notificaciones_no_leidas': 0, 'notificaciones_recientes': []}
    try:
        usuario = request.user.usuario
    except Exception:
        return {'notificaciones_no_leidas': 0, 'notificaciones_recientes': []}
    qs = Notificacion.objects.filter(usuario=usuario, leida=False)
    return {
        'notificaciones_no_leidas': qs.count(),
        'notificaciones_recientes': qs[:5],
    }
