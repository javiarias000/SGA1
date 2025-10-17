from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count, Avg
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date, timedelta
from urllib.parse import quote
from functools import wraps
from django.contrib.auth.models import User
from django.db import IntegrityError

from classes.models import Teacher, Student, Activity, Grade, Attendance, Clase
from classes.forms import StudentForm, ActivityForm, GradeForm, AttendanceForm, TeacherProfileForm


# ============================================
# DECORADOR TEACHER
# ============================================

def teacher_required(view_func):
    """Decorador para vistas que requieren ser docente"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión como docente')
            return redirect('teacher_login')
        
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, '⚠️ No tienes permisos de docente')
            logout(request)
            return redirect('teacher_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================
# LOGIN Y REGISTRO DOCENTE
# ============================================

def teacher_login_view(request):
    """Vista de login para docentes"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'teacher_profile'):
            return redirect('teacher_dashboard')
        elif hasattr(request.user, 'student_profile'):
            messages.info(request, 'Estás en el área de docentes. Usa el login de estudiantes.')
            return redirect('student_dashboard')
        logout(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not hasattr(user, 'teacher_profile'):
                messages.error(request, '⚠️ Esta cuenta no es de docente.')
                return render(request, 'teachers/login.html')
            
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.first_name or user.username}!')
            return redirect('teacher_dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'teachers/login.html')


def teacher_register_view(request):
    """Vista para registrar nuevos docentes"""
    if request.user.is_authenticated:
        return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone', '')
        specialization = request.POST.get('specialization', '')
        
        if not all([username, email, password1, password2, first_name, last_name]):
            messages.error(request, 'Por favor completa todos los campos obligatorios')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden')
        elif len(password1) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado')
        else:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=first_name,
                    last_name=last_name
                )
                teacher = user.teacher_profile
                teacher.full_name = f"{first_name} {last_name}"
                teacher.phone = phone
                teacher.specialization = specialization
                teacher.save()
                
                messages.success(request, f'¡Cuenta creada exitosamente! Ya puedes iniciar sesión como {username}')
                return redirect('teacher_login')
            except IntegrityError:
                messages.error(request, 'Error al crear la cuenta. Intenta con otro nombre de usuario')

    return render(request, 'teachers/register.html')


def teacher_logout_view(request):
    """Cerrar sesión"""
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente')
    return redirect('teacher_login')


# ============================================
# DASHBOARD DOCENTE
# ============================================

@teacher_required
def teacher_dashboard_view(request):
    teacher = request.user.teacher_profile
    clases_teoricas = Clase.objects.filter(teacher=teacher).order_by('-fecha')
    
    clases_con_datos = []
    clases_registradas_count = 0

    for clase in clases_teoricas:
        try:
            registro = clase.registros.get()
            asistencias_count = registro.asistencias.count()
            total_estudiantes = clase.estudiantes.count()
            clases_con_datos.append({
                'clase': clase,
                'tiene_registro': True,
                'asistencias_registradas': asistencias_count,
                'total_estudiantes': total_estudiantes,
                'porcentaje': int((asistencias_count / total_estudiantes * 100)) if total_estudiantes > 0 else 0
            })
            clases_registradas_count += 1
        except Activity.DoesNotExist:
            clases_con_datos.append({
                'clase': clase,
                'tiene_registro': False,
                'total_estudiantes': clase.estudiantes.count()
            })
    
    total_clases = clases_teoricas.count()
    
    context = {
        'teacher': teacher,
        'clases_teoricas': clases_con_datos,
        'total_clases': total_clases,
        'clases_registradas': clases_registradas_count,
        'clases_pendientes': total_clases - clases_registradas_count,
        'total_estudiantes': teacher.students.count(),
    }
    
    return render(request, 'teachers/dashboard.html', context)


# ============================================
# ESTUDIANTES - GESTIÓN
# ============================================

@teacher_required
def estudiantes_view(request):
    """Gestionar estudiantes"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.teacher = teacher
            student.save()
            messages.success(request, f'Estudiante {student.name} agregado')
            return redirect('estudiantes')
    else:
        form = StudentForm()
    
    search = request.GET.get('search', '')
    grade_filter = request.GET.get('grade', '')
    
    students = teacher.students.filter(active=True)
    
    if search:
        students = students.filter(
            Q(name__icontains=search) | 
            Q(parent_name__icontains=search)
        )
    
    if grade_filter:
        students = students.filter(grade=grade_filter)
    
    students = students.annotate(class_count=Count('activities')).order_by('name')
    
    return render(request, 'teachers/estudiantes.html', {
        'form': form,
        'students': students,
        'search': search,
        'grade_filter': grade_filter,
    })


@teacher_required
def student_detail_view(request, student_id):
    """Detalle de estudiante"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    activities = student.activities.all().order_by('-date')
    grades = student.grades.all().order_by('-date')
    
    subjects_stats = {}
    for subject_code, subject_name in Activity.SUBJECT_CHOICES:
        count = activities.filter(subject=subject_code).count()
        if count > 0:
            subjects_stats[subject_name] = count
    
    return render(request, 'teachers/student_detail.html', {
        'student': student,
        'activities': activities,
        'grades': grades,
        'subjects_stats': subjects_stats,
    })


@teacher_required
def student_edit_view(request, student_id):
    """Editar estudiante"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Información de {student.name} actualizada')
            return redirect('student_detail', student_id=student.id)
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'teachers/student_edit.html', {
        'form': form,
        'student': student
    })


@teacher_required
def student_delete_view(request, student_id):
    """Desactivar estudiante"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if request.method == 'POST':
        if student.user:
            student.user.is_active = False
            student.user.save()
        
        student.active = False
        student.save()
        messages.success(request, f'Estudiante {student.name} desactivado')
        return redirect('estudiantes')
    
    return render(request, 'teachers/student_confirm_delete.html', {'student': student})


@teacher_required
def student_code_view(request, student_id):
    """Código de estudiante para registro"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    return render(request, 'teachers/student_code.html', {'student': student})


# ============================================
# ACTIVIDADES/CLASES
# ============================================

@teacher_required
def registro_view(request):
    """Registrar clase"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, teacher=teacher)
        if form.is_valid():
            activity = form.save(commit=False)
            
            last_class = Activity.objects.filter(
                student=activity.student,
                subject=activity.subject
            ).order_by('-class_number').first()
            
            activity.class_number = (last_class.class_number + 1) if last_class else 1
            activity.save()
            
            messages.success(request, f'Clase #{activity.class_number} registrada')
            return redirect('registro')
    else:
        form = ActivityForm(teacher=teacher)
    
    return render(request, 'teachers/registro.html', {
        'form': form,
        'students': teacher.students.filter(active=True)
    })


@teacher_required
def activity_edit_view(request, activity_id):
    """Editar clase"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clase actualizada')
            return redirect('informes')
    else:
        form = ActivityForm(instance=activity, teacher=teacher)
    
    return render(request, 'teachers/activity_edit.html', {
        'form': form,
        'activity': activity
    })


@teacher_required
def activity_delete_view(request, activity_id):
    """Eliminar clase"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    if request.method == 'POST':
        student_name = activity.student.name
        class_number = activity.class_number
        activity.delete()
        messages.success(request, f'Clase #{class_number} de {student_name} eliminada')
        return redirect('informes')
    
    return render(request, 'teachers/activity_confirm_delete.html', {'activity': activity})


# ============================================
# INFORMES
# ============================================

@teacher_required
def informes_view(request):
    """Ver informes"""
    teacher = request.user.teacher_profile
    activities = Activity.objects.filter(
        student__teacher=teacher
    ).select_related('student').order_by('-date')
    
    student_id = request.GET.get('student')
    subject = request.GET.get('subject')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if student_id:
        activities = activities.filter(student_id=student_id)
    if subject:
        activities = activities.filter(subject=subject)
    if date_from:
        activities = activities.filter(date__gte=date_from)
    if date_to:
        activities = activities.filter(date__lte=date_to)
    
    return render(request, 'teachers/informes.html', {
        'activities': activities,
        'students': teacher.students.filter(active=True),
        'selected_student': student_id,
        'selected_subject': subject,
        'date_from': date_from,
        'date_to': date_to,
    })


@teacher_required
def carpetas_view(request):
    """Vista para ver carpetas organizadas por Materia → Estudiante → Clases"""
    teacher = request.user.teacher_profile
    
    activities = Activity.objects.filter(
        student__teacher=teacher,
        student__active=True
    ).select_related('student').order_by('subject', 'student__name', 'class_number')
    
    folders_by_subject = {}
    
    for activity in activities:
        subject = activity.subject
        
        if subject not in folders_by_subject:
            folders_by_subject[subject] = {
                'student_count': 0,
                'total_classes': 0,
                'students': {}
            }
        
        student_id = activity.student.id
        if student_id not in folders_by_subject[subject]['students']:
            folders_by_subject[subject]['students'][student_id] = {
                'student': activity.student,
                'class_count': 0,
                'activities': []
            }
            folders_by_subject[subject]['student_count'] += 1
        
        folders_by_subject[subject]['students'][student_id]['activities'].append(activity)
        folders_by_subject[subject]['students'][student_id]['class_count'] += 1
        folders_by_subject[subject]['total_classes'] += 1
    
    for subject in folders_by_subject:
        folders_by_subject[subject]['students'] = list(
            folders_by_subject[subject]['students'].values()
        )
        folders_by_subject[subject]['students'].sort(
            key=lambda x: x['student'].name
        )
    
    return render(request, 'teachers/carpetas.html', {
        'folders_by_subject': folders_by_subject
    })


@teacher_required
def report_card_view(request, student_id):
    """Libreta de calificaciones"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    activities = student.activities.all().order_by('subject', 'class_number')
    grades = student.grades.all().order_by('subject', 'period')
    attendances = student.attendances.all().order_by('-date')
    
    activities_by_subject = {}
    grades_by_subject = {}
    
    for activity in activities:
        if activity.subject not in activities_by_subject:
            activities_by_subject[activity.subject] = []
        activities_by_subject[activity.subject].append(activity)
    
    for grade in grades:
        if grade.subject not in grades_by_subject:
            grades_by_subject[grade.subject] = []
        grades_by_subject[grade.subject].append(grade)
    
    total_attendance = attendances.count()
    presente_count = attendances.filter(status='Presente').count()
    ausente_count = attendances.filter(status='Ausente').count()
    tardanza_count = attendances.filter(status='Tardanza').count()
    
    attendance_percentage = (presente_count / total_attendance * 100) if total_attendance > 0 else 0
    promedio_general = sum(float(g.score) for g in grades) / len(grades) if grades else 0
    
    context = {
        'student': student,
        'teacher': teacher,
        'activities_by_subject': activities_by_subject,
        'grades_by_subject': grades_by_subject,
        'attendances': attendances[:30],
        'total_attendance': total_attendance,
        'presente_count': presente_count,
        'ausente_count': ausente_count,
        'tardanza_count': tardanza_count,
        'attendance_percentage': attendance_percentage,
        'promedio_general': promedio_general,
        'total_classes': activities.count(),
    }
    
    return render(request, 'teachers/report_card.html', context)


# ============================================
# CALIFICACIONES
# ============================================

@teacher_required
def grades_view(request):
    """Gestionar calificaciones"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = GradeForm(request.POST, teacher=teacher)
        if form.is_valid():
            grade = form.save()
            messages.success(request, f'Calificación registrada: {grade.student.name} - {grade.score}')
            return redirect('grades')
    else:
        form = GradeForm(teacher=teacher)
    
    student_id = request.GET.get('student')
    subject = request.GET.get('subject')
    
    grades = Grade.objects.filter(student__teacher=teacher).select_related('student')
    
    if student_id:
        grades = grades.filter(student_id=student_id)
    if subject:
        grades = grades.filter(subject=subject)
    
    grades = grades.order_by('-date')
    
    return render(request, 'teachers/grades.html', {
        'form': form,
        'grades': grades,
        'students': teacher.students.filter(active=True),
        'selected_student': student_id,
        'selected_subject': subject,
    })


@teacher_required
def grade_edit_view(request, grade_id):
    """Editar calificación"""
    teacher = request.user.teacher_profile
    grade = get_object_or_404(Grade, id=grade_id, student__teacher=teacher)
    
    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Calificación actualizada')
            return redirect('grades')
    else:
        form = GradeForm(instance=grade, teacher=teacher)
    
    return render(request, 'teachers/grade_edit.html', {
        'form': form,
        'grade': grade
    })


@teacher_required
def grade_delete_view(request, grade_id):
    """Eliminar calificación"""
    teacher = request.user.teacher_profile
    grade = get_object_or_404(Grade, id=grade_id, student__teacher=teacher)
    
    if request.method == 'POST':
        student_name = grade.student.name
        grade.delete()
        messages.success(request, f'Calificación de {student_name} eliminada')
        return redirect('grades')
    
    return render(request, 'teachers/grade_confirm_delete.html', {'grade': grade})


# ============================================
# ASISTENCIA
# ============================================

@teacher_required
def attendance_view(request):
    """Control de asistencia"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, teacher=teacher)
        if form.is_valid():
            attendance = form.save()
            messages.success(request, f'Asistencia registrada: {attendance.student.name} - {attendance.status}')
            return redirect('attendance')
    else:
        form = AttendanceForm(teacher=teacher)
    
    today = date.today()
    attendances = Attendance.objects.filter(
        student__teacher=teacher,
        date=today
    ).select_related('student').order_by('student__name')
    
    return render(request, 'teachers/attendance.html', {
        'form': form,
        'attendances': attendances,
        'today': today,
    })


@teacher_required
def attendance_edit_view(request, attendance_id):
    """Editar asistencia"""
    teacher = request.user.teacher_profile
    attendance = get_object_or_404(Attendance, id=attendance_id, student__teacher=teacher)
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Asistencia actualizada')
            return redirect('attendance')
    else:
        form = AttendanceForm(instance=attendance, teacher=teacher)
    
    return render(request, 'teachers/attendance_edit.html', {
        'form': form,
        'attendance': attendance
    })


@teacher_required
def attendance_delete_view(request, attendance_id):
    """Eliminar asistencia"""
    teacher = request.user.teacher_profile
    attendance = get_object_or_404(Attendance, id=attendance_id, student__teacher=teacher)
    
    if request.method == 'POST':
        attendance.delete()
        messages.success(request, 'Registro eliminado')
        return redirect('attendance')
    
    return render(request, 'teachers/attendance_confirm_delete.html', {'attendance': attendance})


# ============================================
# PERFIL
# ============================================

@teacher_required
def profile_view(request):
    """Perfil del docente"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = TeacherProfileForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado')
            return redirect('teacher_profile')
    else:
        form = TeacherProfileForm(instance=teacher)
    
    return render(request, 'teachers/profile.html', {
        'form': form,
        'teacher': teacher,
    })


# ============================================
# API ENDPOINTS
# ============================================

@teacher_required
def get_class_number(request):
    """API para obtener número de clase"""
    teacher = request.user.teacher_profile
    student_id = request.GET.get('student_id')
    subject = request.GET.get('subject')
    
    if not student_id or not subject:
        return JsonResponse({'class_number': 1})
    
    try:
        student = Student.objects.get(id=student_id, teacher=teacher)
        last_class = Activity.objects.filter(
            student=student,
            subject=subject
        ).order_by('-class_number').first()
        
        class_number = (last_class.class_number + 1) if last_class else 1
        
        return JsonResponse({
            'class_number': class_number,
            'total_classes': student.get_class_count(subject)
        })
    except Student.DoesNotExist:
        return JsonResponse({'class_number': 1})


@teacher_required
def get_student_subjects(request):
    """API para obtener materias de estudiante"""
    teacher = request.user.teacher_profile
    student_id = request.GET.get('student_id')
    
    if not student_id:
        return JsonResponse({'subjects': []})
    
    try:
        student = Student.objects.get(id=student_id, teacher=teacher)
        subjects = []
        
        for subject_code, subject_name in Activity.SUBJECT_CHOICES:
            if student.can_take_subject(subject_code):
                class_count = student.get_class_count(subject_code)
                subjects.append({
                    'code': subject_code,
                    'name': subject_name,
                    'class_count': class_count
                })
        
        return JsonResponse({'subjects': subjects})
    except Student.DoesNotExist:
        return JsonResponse({'subjects': []})