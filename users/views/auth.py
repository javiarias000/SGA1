from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from teachers.models import Teacher

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from teachers.models import Teacher
from users.models import Usuario
from django.db import IntegrityError


def unified_login_view(request):
    """Login unificado para docentes y estudiantes."""
    # Resolver next (admite GET o POST)
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.user.is_authenticated:
        # Si ya está logueado, respeta "next" si apunta a un área válida
        if next_url and (next_url.startswith('/students/') or next_url.startswith('/teachers/')):
            return redirect(next_url)
        # Check profiles directly from request.user.usuario
        if hasattr(request.user, 'usuario'):
            if request.user.usuario.rol == Usuario.Rol.ESTUDIANTE and hasattr(request.user.usuario, 'student_profile'):
                return redirect('students:student_dashboard')
            elif request.user.usuario.rol == Usuario.Rol.DOCENTE and hasattr(request.user.usuario, 'teacher_profile'):
                return redirect('teachers:teacher_dashboard')
            else:
                # Usuario exists but no matching role profile (e.g., PENDIENTE or missing specific profile)
                logout(request)
                messages.warning(request, 'Tu cuenta no tiene un perfil de rol asignado (Estudiante/Docente).')
                return redirect('users:login')
        else:
            logout(request)
            messages.warning(request, 'Tu cuenta no tiene un perfil asignado.')
            return redirect('users:login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # After login, the user object might not immediately have middleware-attached profiles.
            # It's safer to check the associated Usuario object directly.
            # We need to re-fetch the user or assume request.user now has its attributes
            # Or, best, just use the `user` object directly and its relations if they exist
            if hasattr(user, 'usuario'): # Check if Usuario object exists
                if user.usuario.rol == Usuario.Rol.ESTUDIANTE and hasattr(user.usuario, 'student_profile'):
                    return redirect('students:student_dashboard')
                elif user.usuario.rol == Usuario.Rol.DOCENTE and hasattr(user.usuario, 'teacher_profile'):
                    return redirect('teachers:teacher_dashboard')
                else:
                    # Usuario exists but no matching role profile (e.g., PENDIENTE or missing specific profile)
                    logout(request)
                    messages.error(request, 'Tu cuenta no tiene un perfil de rol asignado (Estudiante/Docente).')
            else:
                # User authenticated but no Usuario object exists at all
                logout(request)
                messages.error(request, 'Tu cuenta no tiene un perfil asignado.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'users/login.html')



from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction # Importaciones clave

# Asume que estos modelos están disponibles en el contexto de tu vista
from teachers.models import Teacher 
# from students.models import Student ya está importado dentro de la función
User = get_user_model()


def unified_register_view(request):
    from students.models import Student
    """Vista de registro unificada para docentes y estudiantes."""
    if request.method == 'POST':
        role = request.POST.get('role')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # --- 1. VALIDACIÓN BÁSICA ---
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'users/register.html')

        # --- 2. VALIDACIÓN DE UNICIDAD DE USUARIO ---
        if User.objects.filter(username=username).exists():
            messages.error(request, f"El nombre de usuario '{username}' ya existe. Por favor, elija otro.")
            return render(request, 'users/register.html')
        
        # También es buena práctica verificar el email
        if User.objects.filter(email=email).exists():
            messages.error(request, 'La dirección de correo electrónico ya está registrada.')
            return render(request, 'users/register.html')

        # --- 3. PROCESO DE REGISTRO EN TRANSACCIÓN ATÓMICA ---
        # Si algo falla dentro de este bloque, se hace un ROLLBACK de todo.
        try:
            with transaction.atomic(): 
                if role == 'teacher':
                    phone = request.POST.get('phone', '')
                    specialization = request.POST.get('specialization', '')

                    # 3a. Creación del usuario
                    user = User.objects.create_user(
                        username=username, email=email, password=password1,
                        first_name=first_name, last_name=last_name
                    )
                    # 3b. Creación del perfil secundario
                    Teacher.objects.create(user=user, phone=phone, specialization=specialization)
                    
                    messages.success(request, 'Docente registrado correctamente.')
                    return redirect('users:login')

                elif role == 'student':
                    student_code = request.POST.get('student_code', '').strip()
                    try:
                        student = Student.objects.get(registration_code=student_code, active=True)
                    except (Student.DoesNotExist, ValueError):
                        # Si el código es inválido, mostramos error y salimos sin crear el User
                        messages.error(request, 'Código de estudiante inválido.')
                        return render(request, 'users/register.html')

                    if student.user:
                        messages.error(request, 'Este estudiante ya tiene cuenta.')
                        return render(request, 'users/register.html')
                    
                    # 3a. Creación del usuario
                    user = User.objects.create_user(
                        username=username, email=email, password=password1,
                        first_name=first_name, last_name=last_name
                    )
                    # 3b. Vinculación del perfil existente
                    student.user = user
                    student.save()
                    
                    messages.success(request, 'Estudiante registrado correctamente.')
                    return redirect('users:login')

                else:
                    messages.error(request, 'Debes seleccionar un tipo de registro.')

        # --- 4. MANEJO DE ERRORES DE BASE DE DATOS ---
        except IntegrityError as e:
            # Captura errores de unicidad *que no fueron validados antes* (como tu error de secuencia)
            # La transacción.atomic() ya revertirá el user.
            
            # Puedes ser más específico si quieres dar mensajes para errores concretos
            if 'teachers_teacher_user_id_key' in str(e):
                messages.error(request, "Error de registro: Conflicto en la base de datos (clave duplicada). Por favor, contacte al administrador.")
            else:
                messages.error(request, "Error de registro: Los datos proporcionados violan una restricción de la base de datos.")
            
            return render(request, 'users/register.html')

        except Exception as e:
            # Captura cualquier otro error inesperado (ej. problema de conexión a DB)
            messages.error(request, f"Ocurrió un error inesperado al registrar: {e}")
            return render(request, 'users/register.html')
            
    return render(request, 'users/register.html')




from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('home')

@login_required
def change_password_view(request):
    """
    Vista para que el usuario cambie su propia contraseña.
    Es usada por el middleware ForcePasswordChangeMiddleware.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Actualizar la sesión del usuario para que no se desloguee
            update_session_auth_hash(request, user)
            
            # Marcar que el cambio de contraseña ya se ha realizado
            if hasattr(user, 'profile'):
                user.profile.must_change_password = False
                user.profile.save()

            messages.success(request, '¡Tu contraseña ha sido cambiada exitosamente!')
            
            # Redirigir al dashboard correspondiente
            if hasattr(user, 'student_profile'):
                return redirect('students:student_dashboard')
            elif hasattr(user, 'teacher_profile'):
                return redirect('teachers:teacher_dashboard')
            else:
                return redirect('users:login')
        else:
            messages.error(request, 'Por favor corrige los errores señalados.')
    else:
        form = PasswordChangeForm(request.user)

    # Añadir un flag al contexto para saber si el cambio es forzado
    is_forced = request.user.profile.must_change_password
    
    return render(request, 'users/change_password.html', {
        'form': form,
        'is_forced': is_forced
    })
