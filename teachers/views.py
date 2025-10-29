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
from django.contrib.auth.models import User
from django.db import IntegrityError

# Importar decorador de users
from users.views.decorators import teacher_required

# Importar modelos
from teachers.models import Teacher
from students.models import Student
from classes.models import Activity, Grade, Attendance, Clase, Enrollment

# Importar formularios (si existen)
try:
    from classes.forms import StudentForm, ActivityForm, GradeForm, AttendanceForm, TeacherProfileForm, ClaseForm
except ImportError:
    pass


# ============================================
# DASHBOARD DOCENTE
# ============================================

@login_required
@teacher_required
def teacher_dashboard_view(request):
    """Dashboard para docentes con formulario unificado"""
    teacher = request.user.teacher_profile

    # Formulario unificado
    if request.method == 'POST' and request.POST.get('action') == 'save_all_entry':
        from classes.forms import UnifiedEntryForm
        form = UnifiedEntryForm(request.POST, teacher=teacher)
        if form.is_valid():
            from django.db import transaction
            from classes.models import Activity, Attendance, Grade, Clase
            cd = form.cleaned_data
            with transaction.atomic():
                # Asegurar Clase por Materia
                clase = Clase.objects.filter(teacher=teacher, subject=cd['common_subject'], active=True).order_by('name').first()
                if not clase:
                    clase = Clase.objects.create(teacher=teacher, subject=cd['common_subject'], name=cd['common_subject'], active=True)
                # Activity
                last = Activity.objects.filter(student=cd['common_student'], subject=cd['common_subject']).order_by('-class_number').first()
                activity = Activity.objects.create(
                    student=cd['common_student'],
                    clase=clase,
                    subject=cd['common_subject'],
                    class_number=(last.class_number + 1) if last else 1,
                    date=cd['common_date'],
                    topics_worked=cd.get('topics_worked',''),
                    techniques=cd.get('techniques',''),
                    pieces=cd.get('pieces',''),
                    performance=cd['performance'],
                    strengths=cd.get('strengths',''),
                    areas_to_improve=cd.get('areas_to_improve',''),
                    homework=cd.get('homework',''),
                    practice_time=cd.get('practice_time') or 30,
                    observations=cd.get('observations',''),
                )
                # Attendance
                Attendance.objects.update_or_create(
                    student=cd['common_student'], date=cd['common_date'],
                    defaults={'status': cd['attendance_status'], 'notes': cd.get('attendance_notes','')}
                )
                # Grade (opcional)
                if cd.get('grade_score') is not None and cd.get('grade_period'):
                    Grade.objects.update_or_create(
                        student=cd['common_student'], subject=cd['common_subject'], period=cd['grade_period'],
                        defaults={'score': cd['grade_score'], 'comments': cd.get('grade_comments',''), 'date': cd['common_date']}
                    )
            messages.success(request, 'Registro guardado correctamente.')
            return redirect('teachers:teacher_dashboard')
        else:
            # Mostrar errores
            for field, errors in form.errors.items():
                messages.error(request, f"{field}: {','.join(errors)}")
    else:
        from classes.forms import UnifiedEntryForm
        form = UnifiedEntryForm(teacher=teacher)

    # Datos para tarjetas e información del dashboard
    total_students = teacher.students.filter(active=True).count()
    from classes.models import Activity
    recent_activities = Activity.objects.filter(student__teacher=teacher).select_related('student').order_by('-date')[:10]
    total_classes = Activity.objects.filter(student__teacher=teacher).count()
    today = date.today()
    today_classes = Activity.objects.filter(student__teacher=teacher, date=today).select_related('student')
    recent_students = teacher.students.filter(active=True).order_by('name')[:8]

    context = {
        'teacher': teacher,
        'total_students': total_students,
        'total_classes': total_classes,
        'today_classes': today_classes,
        'recent_students': recent_students,
        'recent_activities': recent_activities,
        'unified_form': form,
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
            return redirect('teachers:estudiantes')
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
            return redirect('teachers:student_detail', student_id=student.id)
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
        return redirect('teachers:estudiantes')
    
    return render(request, 'teachers/student_confirm_delete.html', {'student': student})


@teacher_required
def student_code_view(request, student_id):
    """Código de estudiante para registro"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    return render(request, 'teachers/student_code.html', {'student': student})


# ============================================
# CLASES TEÓRICAS (Gestión)
# ============================================

@teacher_required
def clases_teoricas_view(request):
    teacher = request.user.teacher_profile
    if request.method == 'POST':
        form = ClaseForm(request.POST, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clase creada correctamente')
            return redirect('teachers:clases_teoricas')
    else:
        form = ClaseForm(teacher=teacher)
    clases = Clase.objects.filter(teacher=teacher).order_by('subject', 'name')
    return render(request, 'teachers/clases.html', {
        'form': form,
        'clases': clases,
    })

@teacher_required
def clase_create_view(request):
    teacher = request.user.teacher_profile
    if request.method == 'POST':
        form = ClaseForm(request.POST, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clase creada correctamente')
            return redirect('teachers:clases_teoricas')
    else:
        form = ClaseForm(teacher=teacher)
    return render(request, 'teachers/clase_form.html', {'form': form})

@teacher_required
def clase_edit_view(request, clase_id):
    teacher = request.user.teacher_profile
    clase = get_object_or_404(Clase, id=clase_id, teacher=teacher)
    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=clase, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clase actualizada')
            return redirect('teachers:clases_teoricas')
    else:
        form = ClaseForm(instance=clase, teacher=teacher)
    return render(request, 'teachers/clase_form.html', {'form': form, 'clase': clase})

@teacher_required
def clase_delete_view(request, clase_id):
    teacher = request.user.teacher_profile
    clase = get_object_or_404(Clase, id=clase_id, teacher=teacher)
    if request.method == 'POST':
        clase.delete()
        messages.success(request, 'Clase eliminada')
        return redirect('teachers:clases_teoricas')
    return render(request, 'teachers/clase_confirm_delete.html', {'clase': clase})

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
            return redirect('teachers:registro')
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
            return redirect('teachers:informes')
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
        return redirect('teachers:informes')
    
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
            return redirect('teachers:grades')
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
            return redirect('teachers:grades')
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
        return redirect('teachers:grades')
    
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
            return redirect('teachers:attendance')
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
            return redirect('teachers:attendance')
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
        return redirect('teachers:attendance')
    
    return render(request, 'teachers/attendance_confirm_delete.html', {'attendance': attendance})


# ============================================
# PERFIL
# ============================================

@teacher_required
def profile_view(request):
    """Perfil del docente"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = TeacherProfileForm(request.POST, request.FILES, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado')
            return redirect('teachers:profile')
    else:
        form = TeacherProfileForm(instance=teacher)
    
    return render(request, 'teachers/profile.html', {
        'form': form,
        'teacher': teacher,
    })


# ============================================
# DESCARGAS
# ============================================

@teacher_required
def download_parent_report(request, activity_id):
    """Descargar informe para padres"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    content = f"""INFORME DE PROGRESO - MÚSICA
Para Padres de Familia

Fecha: {activity.date.strftime('%d/%m/%Y')}
Clase #{activity.class_number}

Estudiante: {activity.student.name}
Año escolar: {activity.student.grade}
Materia: {activity.subject}
Docente: {teacher.full_name}

TEMAS TRABAJADOS:
{activity.topics_worked or 'No especificado'}

TÉCNICAS:
{activity.techniques or 'No especificado'}

REPERTORIO:
{activity.pieces or 'No especificado'}

DESEMPEÑO: {activity.performance}

FORTALEZAS:
{activity.strengths or 'No especificado'}

ÁREAS DE OPORTUNIDAD:
{activity.areas_to_improve or 'No especificado'}

TAREAS PARA CASA:
{activity.homework or 'No especificado'}

Tiempo de práctica: {activity.practice_time} minutos diarios

OBSERVACIONES:
{activity.observations or 'Ninguna'}

{teacher.full_name}
Docente de Música
    """
    
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    filename = f"{activity.student.name.replace(' ', '_')}_Clase{activity.class_number}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@teacher_required
def download_teacher_report(request, activity_id):
    """Descargar informe para docente"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    content = f"""REGISTRO ACADÉMICO - MÚSICA
Informe para el Docente

Fecha: {activity.date.strftime('%d/%m/%Y')}
ID Registro: #{activity.id}
Clase #{activity.class_number}

ESTUDIANTE: {activity.student.name}
Año escolar: {activity.student.grade}
Materia: {activity.subject}
Docente: {teacher.full_name}

CONTENIDO DE LA CLASE:
{activity.topics_worked or 'No especificado'}

TÉCNICAS:
{activity.techniques or 'No especificado'}

REPERTORIO:
{activity.pieces or 'No especificado'}

EVALUACIÓN: {activity.performance}

NOTAS:
{activity.observations or 'Sin observaciones'}
    """
    
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    filename = f"Docente_{activity.student.name.replace(' ', '_')}_Clase{activity.class_number}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


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


# ============================================
# EMAIL
# ============================================

@teacher_required
def send_report_email(request, activity_id):
    """Enviar informe por email"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    if not activity.student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('teachers:informes')
    
    subject = f"Informe de Clase - {activity.student.name}"
    message = f"""Estimado/a {activity.student.parent_name or 'Padre/Madre'},

Informe de la clase #{activity.class_number}
Estudiante: {activity.student.name}
Materia: {activity.subject}
Fecha: {activity.date.strftime('%d/%m/%Y')}

Desempeño: {activity.performance}

{teacher.full_name}
Docente de Música
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[activity.student.parent_email],
            fail_silently=False,
        )
        messages.success(request, f'✅ Informe enviado a {activity.student.parent_email}')
    except Exception as e:
        messages.error(request, f'❌ Error al enviar email: {str(e)}')
    
    return redirect('teachers:informes')


@teacher_required
def send_grades_email(request, student_id):
    """Enviar calificaciones por email"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('teachers:student_detail', student_id=student.id)
    
    grades = student.grades.all().order_by('subject', '-date')
    subject = f"Calificaciones - {student.name}"
    
    message = f"""Estimado/a {student.parent_name or 'Padre/Madre'},

Calificaciones de {student.name}:

"""
    for grade in grades:
        message += f"{grade.subject}: {grade.score}/10\n"
    
    message += f"\n{teacher.full_name}\nDocente de Música"
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.parent_email],
            fail_silently=False,
        )
        messages.success(request, f'✅ Calificaciones enviadas')
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('teachers:student_detail', student_id=student.id)


# ============================================
# WHATSAPP
# ============================================

def generate_whatsapp_url(phone_number, message):
    """Genera URL de WhatsApp"""
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    if not clean_phone.startswith('593') and len(clean_phone) == 10:
        clean_phone = '593' + clean_phone
    encoded_message = quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"


@teacher_required
def whatsapp_class_report(request, activity_id):
    """Enviar informe por WhatsApp"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    if not activity.student.parent_phone:
        messages.error(request, '⚠️ Sin número de teléfono registrado')
        return redirect('teachers:informes')
    
    message = f"""🎼 INFORME DE CLASE

Estudiante: {activity.student.name}
Clase #{activity.class_number}
Fecha: {activity.date.strftime('%d/%m/%Y')}
Materia: {activity.subject}

Desempeño: {activity.performance}

{teacher.full_name}
Docente de Música
    """
    
    whatsapp_url = generate_whatsapp_url(activity.student.parent_phone, message)
    return redirect(whatsapp_url)


@teacher_required
def whatsapp_grades_report(request, student_id):
    """Enviar calificaciones por WhatsApp"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_phone:
        messages.error(request, '⚠️ Sin número de teléfono')
        return redirect('teachers:student_detail', student_id=student.id)
    
    grades = student.grades.all().order_by('subject')
    message = f"📊 CALIFICACIONES\n\nEstudiante: {student.name}\n\n"
    
    for grade in grades:
        message += f"{grade.subject}: {grade.score}/10\n"
    
    message += f"\n{teacher.full_name}"
    
    whatsapp_url = generate_whatsapp_url(student.parent_phone, message)
    return redirect(whatsapp_url)


@teacher_required
def whatsapp_attendance_report(request, student_id):
    """Enviar asistencia por WhatsApp"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_phone:
        messages.error(request, '⚠️ Sin número de teléfono')
        return redirect('teachers:student_detail', student_id=student.id)
    
    attendances = student.attendances.all()[:10]
    total = attendances.count()
    presente = attendances.filter(status='Presente').count()
    
    message = f"✅ ASISTENCIA\n\nEstudiante: {student.name}\n"
    message += f"Total: {total}\nPresente: {presente}\n\n"
    
    for att in attendances[:5]:
        message += f"{att.date.strftime('%d/%m')}: {att.status}\n"
    
    message += f"\n{teacher.full_name}"
    
    whatsapp_url = generate_whatsapp_url(student.parent_phone, message)
    return redirect(whatsapp_url)