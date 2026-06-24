from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate


def _get_user_profile(user):
    """Extract rol, nombre, email, student_id from a Django auth User."""
    rol = 'ADMIN' if (user.is_staff or user.is_superuser) else 'ESTUDIANTE'
    nombre = user.get_full_name() or user.username
    email = user.email
    student_id = None

    try:
        usuario = user.usuario
        rol = usuario.rol or rol
        nombre = usuario.nombre or nombre
        email = usuario.email or email
        if rol == 'ESTUDIANTE':
            try:
                student_id = usuario.student_profile.pk
            except Exception:
                pass
    except Exception:
        pass

    if user.is_staff or user.is_superuser:
        rol = 'ADMIN'

    return rol, nombre, email, student_id


@csrf_exempt                        # bypass CsrfViewMiddleware antes de que DRF lo vea
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])         # sin SessionAuthentication → sin CSRF check de DRF
def login_with_profile(request):
    """Login extendido — devuelve token + datos del perfil para la app móvil."""
    username = request.data.get('username', '')
    password = request.data.get('password', '')

    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({'error': 'Credenciales incorrectas.'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    rol, nombre, email, student_id = _get_user_profile(user)

    return Response({
        'token': token.key,
        'rol': rol,
        'nombre': nombre,
        'email': email,
        'is_staff': user.is_staff or user.is_superuser,
        'student_id': student_id,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def me_view(request):
    """Datos del usuario autenticado actual."""
    user = request.user
    rol, nombre, email, student_id = _get_user_profile(user)

    return Response({
        'rol': rol,
        'nombre': nombre,
        'email': email,
        'is_staff': user.is_staff or user.is_superuser,
        'student_id': student_id,
    })
