from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date, timedelta
from urllib.parse import quote
from functools import wraps

from .models import Teacher, Student, Activity, Grade, Attendance, Clase
from .forms import StudentForm, ActivityForm, GradeForm, AttendanceForm, TeacherProfileForm
from django.contrib.auth.models import User
from django.db import IntegrityError


from functools import wraps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q, Avg
from django.shortcuts import render, redirect
from users.views.decorators import teacher_required, student_required


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
    
    return render(request, 'classes/estudiantes.html', {
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
    
    return render(request, 'classes/student_detail.html', {
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
    
    return render(request, 'classes/student_edit.html', {
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
    
    return render(request, 'classes/student_confirm_delete.html', {'student': student})


@teacher_required
def student_code_view(request, student_id):
    """Código de estudiante para registro"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    return render(request, 'classes/student_code.html', {'student': student})


#==========================================
#MATRICULA ESTUDIANTES
#==========================================

@student_required
def enroll_in_class_view(request, clase_id):
    """Permite que el estudiante se matricule a una clase"""
    student = request.user.student_profile
    clase = get_object_or_404(Clase, id=clase_id)

    # Verificar si ya está matriculado
    if Enrollment.objects.filter(student=student, clase=clase).exists():
        messages.info(request, "Ya estás matriculado en esta clase.")
    else:
        Enrollment.objects.create(student=student, clase=clase)
        messages.success(request, f"Te has matriculado correctamente en {clase.name}")

    return redirect('student_classes')



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
    
    return render(request, 'classes/registro.html', {
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
    
    return render(request, 'classes/activity_edit.html', {
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
    
    return render(request, 'classes/activity_confirm_delete.html', {'activity': activity})


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
    
    return render(request, 'classes/informes.html', {
        'activities': activities,
        'students': teacher.students.filter(active=True),
        'selected_student': student_id,
        'selected_subject': subject,
        'date_from': date_from,
        'date_to': date_to,
    })


@teacher_required
def carpetas_view(request):
    """Carpetas de estudiantes"""
    teacher = request.user.teacher_profile
    student_id = request.GET.get('student')
    student = None
    activities_by_subject = {}
    
    if student_id:
        student = get_object_or_404(Student, id=student_id, teacher=teacher)
        activities = Activity.objects.filter(student=student).order_by('subject', 'class_number')
        
        for activity in activities:
            if activity.subject not in activities_by_subject:
                activities_by_subject[activity.subject] = []
            activities_by_subject[activity.subject].append(activity)
    
    return render(request, 'classes/carpetas.html', {
        'students': teacher.students.filter(active=True),
        'selected_student': student,
        'activities_by_subject': activities_by_subject
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
    
    return render(request, 'classes/report_card.html', context)


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
    
    return render(request, 'classes/grades.html', {
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
    
    return render(request, 'classes/grade_edit.html', {
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
    
    return render(request, 'classes/grade_confirm_delete.html', {'grade': grade})


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
    
    return render(request, 'classes/attendance.html', {
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
    
    return render(request, 'classes/attendance_edit.html', {
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
    
    return render(request, 'classes/attendance_confirm_delete.html', {'attendance': attendance})


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
            return redirect('profile')
    else:
        form = TeacherProfileForm(instance=teacher)
    
    return render(request, 'classes/profile.html', {
        'form': form,
        'teacher': teacher,
    })


# ============================================
# VISTAS DE ESTUDIANTES
# ============================================

@student_required
def student_classes_view(request):
    """Clases del estudiante"""
    student = request.user.student_profile
    subject_filter = request.GET.get('subject', '')
    
    activities = Activity.objects.filter(student=student).order_by('-date')
    
    if subject_filter:
        activities = activities.filter(subject=subject_filter)
    
    activities_by_subject = {}
    for activity in activities:
        if activity.subject not in activities_by_subject:
            activities_by_subject[activity.subject] = []
        activities_by_subject[activity.subject].append(activity)
    
    return render(request, 'classes/student/classes.html', {
        'student': student,
        'activities': activities,
        'activities_by_subject': activities_by_subject,
        'subject_filter': subject_filter,
    })


@student_required
def student_grades_view(request):
    """Calificaciones del estudiante"""
    student = request.user.student_profile
    grades = Grade.objects.filter(student=student).order_by('subject', '-date')
    
    grades_by_subject = {}
    for grade in grades:
        if grade.subject not in grades_by_subject:
            grades_by_subject[grade.subject] = {
                'grades': [],
                'average': 0
            }
        grades_by_subject[grade.subject]['grades'].append(grade)
    
    for subject in grades_by_subject:
        subject_grades = grades_by_subject[subject]['grades']
        if subject_grades:
            avg = sum(float(g.score) for g in subject_grades) / len(subject_grades)
            grades_by_subject[subject]['average'] = round(avg, 2)
    
    promedio_general = 0
    if grades:
        promedio_general = sum(float(g.score) for g in grades) / len(grades)
        promedio_general = round(promedio_general, 2)
    
    return render(request, 'classes/student/grades.html', {
        'student': student,
        'grades_by_subject': grades_by_subject,
        'promedio_general': promedio_general,
    })


@student_required
def student_attendance_view(request):
    """Asistencia del estudiante"""
    student = request.user.student_profile
    attendances = Attendance.objects.filter(student=student).order_by('-date')
    
    total = attendances.count()
    presente = attendances.filter(status='Presente').count()
    ausente = attendances.filter(status='Ausente').count()
    tardanza = attendances.filter(status='Tardanza').count()
    justificado = attendances.filter(status='Justificado').count()
    
    presente_pct = (presente / total * 100) if total > 0 else 0
    
    return render(request, 'classes/student/attendance.html', {
        'student': student,
        'attendances': attendances,
        'total': total,
        'presente': presente,
        'ausente': ausente,
        'tardanza': tardanza,
        'justificado': justificado,
        'presente_pct': round(presente_pct, 1),
    })


@student_required
def student_profile_view(request):
    """Perfil del estudiante"""
    student = request.user.student_profile
    
    return render(request, 'classes/student/profile.html', {
        'student': student,
    })


# ============================================
# DESCARGAS DE INFORMES
# ============================================

@teacher_required
def download_parent_report(request, activity_id):
    """Descargar informe para padres"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    content = f"""
╔═══════════════════════════════════════════════════════╗
║          INFORME DE PROGRESO - MÚSICA                 ║
║              PARA PADRES DE FAMILIA                   ║
╚═══════════════════════════════════════════════════════╝

📅 Fecha: {activity.date.strftime('%d de %B de %Y')}
📚 Clase #{activity.class_number}

👤 Estudiante: {activity.student.name}
📚 Año escolar: {activity.student.grade}
🎵 Materia: {activity.subject}
👨‍🏫 Docente: {teacher.full_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 LO QUE TRABAJAMOS EN CLASE:

Temas: {activity.topics_worked or 'No especificado'}
Técnicas: {activity.techniques or 'No especificado'}
Repertorio: {activity.pieces or 'No especificado'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⭐ DESEMPEÑO: {activity.performance}

✨ Fortalezas observadas:
{activity.strengths or 'No especificado'}

🎯 Áreas de oportunidad:
{activity.areas_to_improve or 'No especificado'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 TAREAS PARA CASA:

{activity.homework or 'No especificado'}

⏰ Tiempo de práctica recomendado: {activity.practice_time} minutos diarios

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Observaciones adicionales:
{activity.observations or 'Ninguna'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Gracias por su apoyo en el proceso de aprendizaje musical.
La práctica constante es clave para el progreso.

{teacher.full_name}
Docente de Música
    """
    
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    filename = f"{activity.student.name.replace(' ', '_')}_PADRES_Clase{activity.class_number}_{activity.subject.split()[0]}_{activity.date}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@teacher_required
def download_teacher_report(request, activity_id):
    """Descargar informe para docente"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    content = f"""
╔═══════════════════════════════════════════════════════╗
║         REGISTRO ACADÉMICO - MÚSICA                  ║
║           INFORME PARA EL DOCENTE                     ║
╚═══════════════════════════════════════════════════════╝

📅 Fecha de clase: {activity.date.strftime('%d/%m/%Y')}
🆔 ID Registro: #{activity.id}
📚 Clase #{activity.class_number}
👨‍🏫 Docente: {teacher.full_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATOS DEL ESTUDIANTE:
• Nombre: {activity.student.name}
• Año escolar: {activity.student.grade}
• ID Estudiante: {activity.student.id}
• Materia: {activity.subject}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTENIDO DE LA CLASE:

1. Temas trabajados:
   {activity.topics_worked or 'No especificado'}

2. Técnicas desarrolladas:
   {activity.techniques or 'No especificado'}

3. Repertorio:
   {activity.pieces or 'No especificado'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EVALUACIÓN:
• Desempeño general: {activity.performance}

• Aspectos positivos:
  {activity.strengths or 'No especificado'}

• Aspectos a reforzar:
  {activity.areas_to_improve or 'No especificado'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PLAN DE ESTUDIO EN CASA:
{activity.homework or 'No especificado'}

Tiempo sugerido: {activity.practice_time} min/día

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOTAS DEL PROFESOR:
{activity.observations or 'Sin observaciones adicionales'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Registro guardado: {activity.created_at.strftime('%d/%m/%Y %H:%M:%S')}
    """
    
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    filename = f"{activity.student.name.replace(' ', '_')}_DOCENTE_Clase{activity.class_number}_{activity.subject.split()[0]}_{activity.date}.txt"
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
# EMAIL - FUNCIONES
# ============================================

@teacher_required
def send_report_email(request, activity_id):
    """Enviar informe por email"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    if not activity.student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('informes')
    
    subject = f"Informe de Clase - {activity.student.name} - Clase #{activity.class_number}"
    
    message = f"""
Estimado/a {activity.student.parent_name or 'Padre/Madre de familia'},

Le enviamos el informe de la clase de música de {activity.student.name}.

═══════════════════════════════════════════════════════
INFORME DE PROGRESO - MÚSICA
═══════════════════════════════════════════════════════

📅 Fecha: {activity.date.strftime('%d de %B de %Y')}
📚 Clase #{activity.class_number}

👤 Estudiante: {activity.student.name}
📚 Año escolar: {activity.student.grade}
🎵 Materia: {activity.subject}
👨‍🏫 Docente: {teacher.full_name}

───────────────────────────────────────────────────────

📚 LO QUE TRABAJAMOS EN CLASE:

Temas: {activity.topics_worked or 'No especificado'}
Técnicas: {activity.techniques or 'No especificado'}
Repertorio: {activity.pieces or 'No especificado'}

───────────────────────────────────────────────────────

⭐ DESEMPEÑO: {activity.performance}

✨ Fortalezas observadas:
{activity.strengths or 'No especificado'}

🎯 Áreas a mejorar: 
{activity.areas_to_improve or 'No especificado'}

───────────────────────────────────────────────────────

🏠 TAREAS PARA CASA:

{activity.homework or 'No especificado'}

⏰ Tiempo de práctica recomendado: {activity.practice_time} minutos diarios

───────────────────────────────────────────────────────

💡 Observaciones adicionales:
{activity.observations or 'Ninguna'}

───────────────────────────────────────────────────────

Gracias por su apoyo en el proceso de aprendizaje musical.

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
    
    return redirect('informes')


@teacher_required
def send_grades_email(request, student_id):
    """Enviar calificaciones por email"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('student_detail', student_id=student.id)
    
    grades = student.grades.all().order_by('subject', '-date')
    subject = f"Reporte de Calificaciones - {student.name}"
    
    message = f"""
Estimado/a {student.parent_name or 'Padre/Madre de familia'},

Le enviamos el reporte de calificaciones de {student.name}.

═══════════════════════════════════════════════════════
REPORTE DE CALIFICACIONES
═══════════════════════════════════════════════════════

👤 Estudiante: {student.name}
📚 Año escolar: {student.grade}
📅 Fecha del reporte: {datetime.now().strftime('%d de %B de %Y')}
👨‍🏫 Docente: {teacher.full_name}

───────────────────────────────────────────────────────
CALIFICACIONES:
───────────────────────────────────────────────────────

"""
    
    for grade in grades:
        message += f"""
📊 {grade.subject}
   Período: {grade.period}
   Calificación: {grade.score} / 10
   Fecha: {grade.date.strftime('%d/%m/%Y')}
   Comentarios: {grade.comments or 'Sin comentarios'}
   
"""
    
    message += f"""
───────────────────────────────────────────────────────

Saludos cordiales,
{teacher.full_name}
Docente de Música
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.parent_email],
            fail_silently=False,
        )
        messages.success(request, f'✅ Calificaciones enviadas a {student.parent_email}')
    except Exception as e:
        messages.error(request, f'❌ Error al enviar email: {str(e)}')
    
    return redirect('student_detail', student_id=student.id)


@teacher_required
def send_attendance_report(request, student_id):
    """Enviar reporte de asistencia por email"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('student_detail', student_id=student.id)
    
    attendances = student.attendances.all().order_by('-date')[:30]
    
    total = attendances.count()
    presente = attendances.filter(status='Presente').count()
    ausente = attendances.filter(status='Ausente').count()
    tardanza = attendances.filter(status='Tardanza').count()
    justificado = attendances.filter(status='Justificado').count()
    
    subject = f"Reporte de Asistencia - {student.name}"
    
    message = f"""
Estimado/a {student.parent_name or 'Padre/Madre de familia'},

Le enviamos el reporte de asistencia de {student.name}.

═══════════════════════════════════════════════════════
REPORTE DE ASISTENCIA
═══════════════════════════════════════════════════════

👤 Estudiante: {student.name}
📚 Año escolar: {student.grade}
📅 Fecha del reporte: {datetime.now().strftime('%d de %B de %Y')}
👨‍🏫 Docente: {teacher.full_name}

───────────────────────────────────────────────────────
ESTADÍSTICAS (últimos 30 registros):
───────────────────────────────────────────────────────

Total de registros: {total}
✅ Presente: {presente} ({(presente/total*100 if total > 0 else 0):.1f}%)
❌ Ausente: {ausente} ({(ausente/total*100 if total > 0 else 0):.1f}%)
⏰ Tardanza: {tardanza} ({(tardanza/total*100 if total > 0 else 0):.1f}%)
📝 Justificado: {justificado} ({(justificado/total*100 if total > 0 else 0):.1f}%)

───────────────────────────────────────────────────────
DETALLE DE ASISTENCIAS:
───────────────────────────────────────────────────────

"""
    
    for attendance in attendances:
        icon = '✅' if attendance.status == 'Presente' else '❌' if attendance.status == 'Ausente' else '⏰' if attendance.status == 'Tardanza' else '📝'
        message += f"{icon} {attendance.date.strftime('%d/%m/%Y')} - {attendance.status}\n"
        if attendance.notes:
            message += f"   Nota: {attendance.notes}\n"
        message += "\n"
    
    message += f"""
───────────────────────────────────────────────────────

Saludos cordiales,
{teacher.full_name}
Docente de Música
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.parent_email],
            fail_silently=False,
        )
        messages.success(request, f'✅ Reporte enviado a {student.parent_email}')
    except Exception as e:
        messages.error(request, f'❌ Error al enviar email: {str(e)}')
    
    return redirect('student_detail', student_id=student.id)


@teacher_required
def send_complete_report_email(request, student_id):
    """Enviar libreta completa por email"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('report_card', student_id=student.id)
    
    activities = student.activities.all().order_by('-date')[:10]
    grades = student.grades.all().order_by('subject', '-date')
    attendances = student.attendances.all().order_by('-date')[:20]
    
    subject = f"Libreta de Calificaciones Completa - {student.name}"
    
    message = f"""
Estimado/a {student.parent_name or 'Padre/Madre de familia'},

Le enviamos la libreta de calificaciones completa de {student.name}.

═══════════════════════════════════════════════════════
LIBRETA DE CALIFICACIONES - {student.name}
═══════════════════════════════════════════════════════

Año escolar: {student.grade}
Docente: {teacher.full_name}
Fecha: {datetime.now().strftime('%d de %B de %Y')}

Para ver el reporte completo con mejor formato, por favor ingrese al sistema.

Saludos cordiales,
{teacher.full_name}
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.parent_email],
            fail_silently=False,
        )
        messages.success(request, f'✅ Libreta enviada a {student.parent_email}')
    except Exception as e:
        messages.error(request, f'❌ Error al enviar email: {str(e)}')
    
    return redirect('report_card', student_id=student.id)


# ============================================
# WHATSAPP - FUNCIONES AUXILIARES
# ============================================

def generate_whatsapp_url(phone_number, message):
    """Genera URL de WhatsApp con mensaje prellenado"""
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    
    if not clean_phone.startswith('593') and len(clean_phone) == 10:
        clean_phone = '593' + clean_phone
    
    encoded_message = quote(message)
    whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_message}"
    
    return whatsapp_url


def generate_class_report_message(activity):
    """Genera mensaje de informe de clase para WhatsApp"""
    teacher = activity.student.teacher
    
    message = f"""
🎼 *INFORME DE CLASE - MÚSICA* 🎼

📅 *Fecha:* {activity.date.strftime('%d/%m/%Y')}
📚 *Clase #:* {activity.class_number}

👤 *Estudiante:* {activity.student.name}
📖 *Año:* {activity.student.grade}
🎵 *Materia:* {activity.subject}
👨‍🏫 *Docente:* {teacher.full_name}

━━━━━━━━━━━━━━━━━━━━━

📚 *LO QUE TRABAJAMOS EN CLASE:*

*Temas:* {activity.topics_worked or 'No especificado'}
*Técnicas:* {activity.techniques or 'No especificado'}
*Repertorio:* {activity.pieces or 'No especificado'}

━━━━━━━━━━━━━━━━━━━━━

⭐ *DESEMPEÑO:* {activity.performance}

✨ *Fortalezas:*
{activity.strengths or 'No especificado'}

🎯 *Áreas de oportunidad:*
{activity.areas_to_improve or 'No especificado'}

━━━━━━━━━━━━━━━━━━━━━

🏠 *TAREAS PARA CASA:*

{activity.homework or 'No especificado'}

⏰ *Tiempo de práctica:* {activity.practice_time} minutos diarios

━━━━━━━━━━━━━━━━━━━━━

💡 *Observaciones:*
{activity.observations or 'Ninguna'}

━━━━━━━━━━━━━━━━━━━━━

Gracias por su apoyo 🎵

_{teacher.full_name}_
_Docente de Música_
    """.strip()
    
    return message


def generate_grades_message(student):
    """Genera mensaje de calificaciones para WhatsApp"""
    grades = student.grades.all().order_by('subject', '-date')
    teacher = student.teacher
    
    message = f"""
📊 *REPORTE DE CALIFICACIONES* 📊

👤 *Estudiante:* {student.name}
📖 *Año:* {student.grade}
📅 *Fecha:* {datetime.now().strftime('%d/%m/%Y')}
👨‍🏫 *Docente:* {teacher.full_name}

━━━━━━━━━━━━━━━━━━━━━

*CALIFICACIONES:*

"""
    
    for grade in grades:
        message += f"""
📚 *{grade.subject}*
   • Período: {grade.period}
   • Calificación: *{grade.score} / 10*
   • Fecha: {grade.date.strftime('%d/%m/%Y')}
"""
        if grade.comments:
            message += f"   • Comentarios: {grade.comments}\n"
        message += "\n"
    
    if grades:
        promedio = sum(float(g.score) for g in grades) / len(grades)
        message += f"*PROMEDIO GENERAL:* {promedio:.2f} / 10\n\n"
    
    message += f"""━━━━━━━━━━━━━━━━━━━━━

_{teacher.full_name}_
_Docente de Música_
    """.strip()
    
    return message


def generate_attendance_message(student):
    """Genera mensaje de asistencia para WhatsApp"""
    attendances = student.attendances.all().order_by('-date')[:30]
    teacher = student.teacher
    
    total = attendances.count()
    presente = attendances.filter(status='Presente').count()
    ausente = attendances.filter(status='Ausente').count()
    tardanza = attendances.filter(status='Tardanza').count()
    
    presente_pct = (presente / total * 100) if total > 0 else 0
    
    message = f"""
✅ *REPORTE DE ASISTENCIA* ✅

👤 *Estudiante:* {student.name}
📖 *Año:* {student.grade}
📅 *Fecha:* {datetime.now().strftime('%d/%m/%Y')}
👨‍🏫 *Docente:* {teacher.full_name}

━━━━━━━━━━━━━━━━━━━━━

*ESTADÍSTICAS (últimos 30 registros):*

Total: {total}
✅ Presente: {presente} ({presente_pct:.1f}%)
❌ Ausente: {ausente}
⏰ Tardanza: {tardanza}

━━━━━━━━━━━━━━━━━━━━━

*ÚLTIMAS ASISTENCIAS:*

"""
    
    for attendance in attendances[:10]:
        icon = '✅' if attendance.status == 'Presente' else '❌' if attendance.status == 'Ausente' else '⏰'
        message += f"{icon} {attendance.date.strftime('%d/%m/%Y')} - {attendance.status}\n"
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━━

_{teacher.full_name}_
_Docente de Música_
    """.strip()
    
    return message


# ============================================
# WHATSAPP - VISTAS
# ============================================

@teacher_required
def whatsapp_class_report(request, activity_id):
    """Enviar informe de clase por WhatsApp"""
    teacher = request.user.teacher_profile
    activity = get_object_or_404(Activity, id=activity_id, student__teacher=teacher)
    
    if not activity.student.parent_phone:
        messages.error(request, '⚠️ Este estudiante no tiene número de teléfono registrado')
        return redirect('informes')
    
    message = generate_class_report_message(activity)
    whatsapp_url = generate_whatsapp_url(activity.student.parent_phone, message)
    
    return redirect(whatsapp_url)


@teacher_required
def whatsapp_grades_report(request, student_id):
    """Enviar calificaciones por WhatsApp"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_phone:
        messages.error(request, '⚠️ Este estudiante no tiene número de teléfono registrado')
        return redirect('student_detail', student_id=student.id)
    
    message = generate_grades_message(student)
    whatsapp_url = generate_whatsapp_url(student.parent_phone, message)
    
    return redirect(whatsapp_url)


@teacher_required
def whatsapp_attendance_report(request, student_id):
    """Enviar asistencia por WhatsApp"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    
    if not student.parent_phone:
        messages.error(request, '⚠️ Este estudiante no tiene número de teléfono registrado')
        return redirect('student_detail', student_id=student.id)
    
    message = generate_attendance_message(student)
    whatsapp_url = generate_whatsapp_url(student.parent_phone, message)
    
    return redirect(whatsapp_url)

    #=================================
    #Carpetas
    #=================================

@login_required
def carpetas_view(request):
    """Vista para ver carpetas organizadas por Materia → Estudiante → Clases"""
    teacher = request.user.teacher_profile
    
    # Obtener todas las actividades del docente
    activities = Activity.objects.filter(
        student__teacher=teacher,
        student__active=True
    ).select_related('student').order_by('subject', 'student__name', 'class_number')
    
    # DEBUG: Imprimir para verificar
    print(f"Total actividades encontradas: {activities.count()}")
    for act in activities:
        print(f"  - {act.subject} | {act.student.name} | Clase #{act.class_number}")
    
    # Organizar por: Materia → Estudiante → Clases
    folders_by_subject = {}
    
    for activity in activities:
        subject = activity.subject
        
        # Inicializar materia si no existe
        if subject not in folders_by_subject:
            folders_by_subject[subject] = {
                'student_count': 0,
                'total_classes': 0,
                'students': {}
            }
        
        # Inicializar estudiante si no existe en esta materia
        student_id = activity.student.id
        if student_id not in folders_by_subject[subject]['students']:
            folders_by_subject[subject]['students'][student_id] = {
                'student': activity.student,
                'class_count': 0,
                'activities': []
            }
            folders_by_subject[subject]['student_count'] += 1
        
        # Agregar clase
        folders_by_subject[subject]['students'][student_id]['activities'].append(activity)
        folders_by_subject[subject]['students'][student_id]['class_count'] += 1
        folders_by_subject[subject]['total_classes'] += 1
    
    # Convertir dict de estudiantes a lista para el template
    for subject in folders_by_subject:
        folders_by_subject[subject]['students'] = list(
            folders_by_subject[subject]['students'].values()
        )
        # Ordenar estudiantes por nombre
        folders_by_subject[subject]['students'].sort(
            key=lambda x: x['student'].name
        )
    
    # DEBUG: Imprimir estructura final
    print("\nEstructura de carpetas:")
    for subject, data in folders_by_subject.items():
        print(f"\n{subject}: {data['student_count']} estudiantes, {data['total_classes']} clases")
        for student_data in data['students']:
            print(f"  - {student_data['student'].name}: {student_data['class_count']} clases")
    
    return render(request, 'classes/carpetas.html', {
        'folders_by_subject': folders_by_subject
    })