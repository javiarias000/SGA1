from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count, Avg, Prefetch
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date, timedelta
from urllib.parse import quote
from django.contrib.auth.models import User
from django.db import IntegrityError
from datetime import date, timedelta, timezone
from decimal import Decimal

# Importar decorador de users
from users.views.decorators import teacher_required, student_required

# Importar modelos
from teachers.models import Teacher
from students.models import Student
from classes.models import Activity, Grade, Attendance, Clase, Enrollment, CalificacionParcial, TipoAporte, PromedioCache, Deber, DeberEntrega, Curso

# Importar formularios (si existen)
try:
    from classes.forms import StudentForm, ActivityForm, GradeForm, AttendanceForm, TeacherProfileForm, ClaseForm
except ImportError:
    pass


from .forms import DeberForm, DeberEntregaForm, CalificacionForm


# ============================================
# DASHBOARD DOCENTE
# ============================================



def teacher_required(function):
    """Decorator para verificar que el usuario es docente"""
    def wrap(request, *args, **kwargs):
        if hasattr(request.user, 'teacher_profile'):
            return function(request, *args, **kwargs)
        else:
            messages.error(request, 'No tienes permisos para acceder a esta página')
            return redirect('home')
    return wrap


@login_required
@teacher_required
def teacher_dashboard(request):
    """
    Dashboard Unificado con Sistema de Calificaciones Integral
    Único punto de entrada para registro de calificaciones
    """
    teacher = request.user.teacher_profile
    
    # ==========================================
    # MANEJO DE FORMULARIOS
    # ==========================================
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_calificaciones':
            return _guardar_calificaciones(request, teacher)
        
        elif action == 'delete_calificacion':
            return _eliminar_calificacion(request, teacher)

        elif action == 'create_informe':
            # Crear actividad/informe de clase y guardar archivo en static/teachers/reports/
            try:
                student_id = request.POST.get('report_student_id')
                subject = request.POST.get('report_subject')
                date_str = request.POST.get('report_date')
                performance = request.POST.get('report_performance', 'Bueno')
                topics = request.POST.get('report_topics', '')
                techniques = request.POST.get('report_techniques', '')
                pieces = request.POST.get('report_pieces', '')
                observations = request.POST.get('report_observations', '')

                # Validaciones básicas
                if not (student_id and subject and date_str):
                    messages.error(request, 'Datos incompletos para crear el informe')
                    return redirect('teachers:teacher_dashboard')

                student = get_object_or_404(Student, id=student_id, teacher=teacher)
                fecha = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Obtener o crear Clase asociada del docente por materia
                clase = Clase.objects.filter(teacher=teacher, subject=subject).first()
                if not clase:
                    clase = Clase.objects.create(
                        teacher=teacher,
                        name=f"{subject} - {teacher.full_name}",
                        subject=subject,
                        description='Clase auto-creada para informes desde dashboard',
                        active=True
                    )

                # Número de clase se autogenera en save() si se deja en blanco
                activity = Activity(
                    student=student,
                    clase=clase,
                    subject=subject,
                    class_number=0,
                    date=fecha,
                    topics_worked=topics,
                    techniques=techniques,
                    pieces=pieces,
                    performance=performance,
                    observations=observations
                )
                activity.save()

                # Guardar archivo de informe en static/teachers/reports/<student_id>/
                try:
                    import os
                    from django.conf import settings
                    reports_root = os.path.join(settings.BASE_DIR, 'static', 'teachers', 'reports', str(student.id))
                    os.makedirs(reports_root, exist_ok=True)
                    filename = f"Docente_{student.name.replace(' ', '_')}_Clase{activity.class_number}.txt"
                    content = f"""REGISTRO ACADÉMICO - MÚSICA\nInforme para el Docente\n\nFecha: {activity.date.strftime('%d/%m/%Y')}\nID Registro: #{activity.id}\nClase #{activity.class_number}\n\nESTUDIANTE: {student.name}\nAño escolar: {student.grade}\nMateria: {activity.subject}\nDocente: {teacher.full_name}\n\nCONTENIDO DE LA CLASE:\n{activity.topics_worked or 'No especificado'}\n\nTÉCNICAS:\n{activity.techniques or 'No especificado'}\n\nREPERTORIO:\n{activity.pieces or 'No especificado'}\n\nEVALUACIÓN: {activity.performance}\n\nNOTAS:\n{activity.observations or 'Sin observaciones'}\n"""
                    with open(os.path.join(reports_root, filename), 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception:
                    # No bloquear si falla el guardado físico
                    pass

                messages.success(request, f'Informe creado para {student.name} (Clase #{activity.class_number})')
            except Exception as e:
                messages.error(request, f'No se pudo crear el informe: {e}')
            return redirect('teachers:teacher_dashboard')

        elif action == 'unified_save':
            return _guardar_unificado(request, teacher)
    
    # ==========================================
    # CONTEXTO DEL DASHBOARD
    # ==========================================
    
    # Estudiantes activos
    estudiantes = teacher.students.filter(active=True).order_by('name')
    total_students = estudiantes.count()
    
    # Actividades y clases
    total_classes = Activity.objects.filter(student__teacher=teacher).count()
    today = date.today()
    today_classes = Activity.objects.filter(
        student__teacher=teacher, 
        date=today
    ).select_related('student')
    
    # Asistencias de hoy y formulario de asistencia en dashboard
    attendances_today = Attendance.objects.filter(
        student__teacher=teacher,
        date=today
    ).select_related('student').order_by('student__name')
    attendance_form = None
    try:
        attendance_form = AttendanceForm(teacher=teacher)
    except Exception:
        attendance_form = None
    
    # Última semana
    last_week = today - timedelta(days=7)
    recent_activities = Activity.objects.filter(
        student__teacher=teacher,
        date__gte=last_week
    ).select_related('student').order_by('-date')[:10]
    
    # Tipos de aportes para el formulario
    tipos_aportes = TipoAporte.objects.filter(activo=True).order_by('orden')
    
    # Materias disponibles (dinámicas)
    from classes.models import get_all_subjects
    materias = [(s, s) for s in get_all_subjects()]
    
    # Calificaciones recientes
    calificaciones_recientes = CalificacionParcial.objects.filter(
        student__teacher=teacher
    ).select_related('student', 'tipo_aporte').order_by('-fecha_actualizacion')[:20]
    
    # Estadísticas de estudiantes con promedios
    estudiantes_con_stats = []
    for estudiante in estudiantes:
        # Obtener promedio desde cache o calcular
        try:
            cache_promedio = PromedioCache.objects.get(
                student=estudiante,
                subject='GENERAL',
                tipo_promedio='general'
            )
            promedio = float(cache_promedio.promedio)
        except PromedioCache.DoesNotExist:
            promedio = float(CalificacionParcial.calcular_promedio_general(estudiante))
        
        if promedio > 0:
            # Crear instancia temporal para obtener escala
            temp_calif = CalificacionParcial(calificacion=Decimal(str(promedio)))
            escala = temp_calif.get_escala_cualitativa()
            
            estudiantes_con_stats.append({
                'estudiante': estudiante,
                'promedio': promedio,
                'escala': escala,
                'en_riesgo': promedio < 7
            })
    
    # Ordenar por promedio (descendente)
    estudiantes_con_stats.sort(key=lambda x: x['promedio'], reverse=True)
    
    # Top 10 y estudiantes en riesgo
    top_estudiantes = estudiantes_con_stats[:10]
    estudiantes_en_riesgo = [e for e in estudiantes_con_stats if e['en_riesgo']]
    
    # Estadísticas por escala
    stats_por_escala = {
        'DAR': len([e for e in estudiantes_con_stats if e['promedio'] >= 9]),
        'AAR': len([e for e in estudiantes_con_stats if 7 <= e['promedio'] < 9]),
        'PAAR': len([e for e in estudiantes_con_stats if 4.01 <= e['promedio'] < 7]),
        'NAAR': len([e for e in estudiantes_con_stats if 0 < e['promedio'] <= 4]),
    }
    
    # Datos para gráficos
    import json
    nombres = []
    promedios = []
    colores = []
    for est in estudiantes:
        prom = float(CalificacionParcial.calcular_promedio_general(est))
        if prom > 0:
            nombres.append(est.name)
            promedios.append(prom)
            if prom >= 9:
                colores.append('#10B981')
            elif prom >= 7:
                colores.append('#3B82F6')
            elif prom >= 4.01:
                colores.append('#F59E0B')
            else:
                colores.append('#EF4444')

    context = {
        'teacher': teacher,
        'total_students': total_students,
        'total_classes': total_classes,
        'today_classes': today_classes,
        'recent_activities': recent_activities,
        'estudiantes': estudiantes,
        'tipos_aportes': tipos_aportes,
        'materias': materias,
        'calificaciones_recientes': calificaciones_recientes,
        'attendances_today': attendances_today,
        'attendance_form': attendance_form,
        'top_estudiantes': top_estudiantes,
        'estudiantes_en_riesgo': estudiantes_en_riesgo,
        'stats_por_escala': stats_por_escala,
        'parciales': CalificacionParcial.PARCIAL_CHOICES,
        'quimestres': CalificacionParcial.QUIMESTRE_CHOICES,
        'total_estudiantes_evaluados': len(estudiantes_con_stats),
        'estudiantes_nombres': json.dumps(nombres),
        'estudiantes_promedios': json.dumps(promedios),
        'colores_escalas': json.dumps(colores),
    }

    return render(request, 'teachers/dashboard_unified.html', context)


def _guardar_calificaciones(request, teacher):
    """Función auxiliar para guardar calificaciones"""
    try:
        student_id = request.POST.get('student_id')
        subject = request.POST.get('subject')
        parcial = request.POST.get('parcial', '1P')
        quimestre = request.POST.get('quimestre', 'Q1')
        observaciones_generales = request.POST.get('observaciones', '')
        
        # Validar estudiante
        student = get_object_or_404(
            Student, 
            id=student_id, 
            teacher=teacher,
            active=True
        )
        
        calificaciones_guardadas = 0
        
        # Obtener todos los campos que comienzan con 'aporte_nombre_'
        for key in request.POST.keys():
            if key.startswith('aporte_nombre_'):
                index = key.replace('aporte_nombre_', '')
                nombre_aporte = request.POST.get(f'aporte_nombre_{index}', '').strip()
                calificacion_value = request.POST.get(f'aporte_nota_{index}', '').strip()
                
                if nombre_aporte and calificacion_value:
                    try:
                        nota = Decimal(calificacion_value)
                        
                        # Validar rango
                        if nota < 0 or nota > 10:
                            messages.warning(
                                request, 
                                f'⚠️ La nota para {nombre_aporte} debe estar entre 0 y 10'
                            )
                            continue
                        
                        # Crear o buscar el tipo de aporte (generación dinámica)
                        # Generar código único basado en el nombre
                        codigo = nombre_aporte.upper().replace(' ', '_')[:50]
                        
                        tipo_aporte, created = TipoAporte.objects.get_or_create(
                            codigo=codigo,
                            defaults={
                                'nombre': nombre_aporte,
                                'peso': 1.0,
                                'orden': 0,
                                'activo': True
                            }
                        )
                        
                        # Si ya existía pero con diferente nombre, actualizar
                        if not created and tipo_aporte.nombre != nombre_aporte:
                            tipo_aporte.nombre = nombre_aporte
                            tipo_aporte.save()
                        
                        # Observaciones específicas del aporte
                        obs_aporte = request.POST.get(f'obs_{index}', '')
                        observaciones_completas = f"{observaciones_generales}\n{obs_aporte}".strip()
                        
                        # Crear o actualizar calificación
                        calif, created = CalificacionParcial.objects.update_or_create(
                            student=student,
                            subject=subject,
                            parcial=parcial,
                            quimestre=quimestre,
                            tipo_aporte=tipo_aporte,
                            defaults={
                                'calificacion': nota,
                                'observaciones': observaciones_completas,
                                'registrado_por': teacher
                            }
                        )
                        calificaciones_guardadas += 1
                        
                    except (ValueError, TypeError) as e:
                        messages.warning(
                            request,
                            f'⚠️ Valor inválido para {nombre_aporte}: {calificacion_value}'
                        )
                        continue
        
        if calificaciones_guardadas > 0:
            # Calcular promedio del parcial
            promedio_parcial = CalificacionParcial.calcular_promedio_parcial(
                student, subject, parcial, quimestre
            )
            
            messages.success(
                request,
                f'✅ {calificaciones_guardadas} calificación(es) guardada(s) para {student.name}<br>'
                f'📊 Promedio del parcial: <strong>{promedio_parcial}</strong>'
            )
        else:
            messages.info(request, 'ℹ️ No se guardaron calificaciones')
        
    except Exception as e:
        messages.error(request, f'❌ Error al guardar: {str(e)}')
    
    return redirect('teachers:teacher_dashboard')


def _eliminar_calificacion(request, teacher):
    """Función auxiliar para eliminar una calificación"""
    try:
        calif_id = request.POST.get('calificacion_id')
        calificacion = get_object_or_404(
            CalificacionParcial,
            id=calif_id,
            student__teacher=teacher
        )
        
        info = f"{calificacion.student.name} - {calificacion.tipo_aporte.nombre}"
        calificacion.delete()
        
        messages.success(request, f'🗑️ Calificación eliminada: {info}')
        
    except Exception as e:
        messages.error(request, f'❌ Error al eliminar: {str(e)}')
    
    return redirect('teachers:teacher_dashboard')


def _guardar_unificado(request, teacher):
    """Guarda calificaciones, asistencia e informe en un solo envío."""
    try:
        student_id = request.POST.get('student_id')
        subject = request.POST.get('subject')
        parcial = request.POST.get('parcial', '1P')
        quimestre = request.POST.get('quimestre', 'Q1')
        fecha_str = request.POST.get('date')
        observaciones_generales = request.POST.get('observaciones', '')

        if not (student_id and subject and fecha_str):
            messages.error(request, 'Faltan datos: estudiante, materia o fecha')
            return redirect('teachers:teacher_dashboard')

        student = get_object_or_404(Student, id=student_id, teacher=teacher, active=True)
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        # 1) Calificaciones
        calificaciones_guardadas = 0
        for key in request.POST.keys():
            if key.startswith('aporte_nombre_'):
                index = key.replace('aporte_nombre_', '')
                nombre_aporte = request.POST.get(f'aporte_nombre_{index}', '').strip()
                calificacion_value = request.POST.get(f'aporte_nota_{index}', '').strip()
                obs_aporte = request.POST.get(f'obs_{index}', '')
                if not (nombre_aporte and calificacion_value):
                    continue
                try:
                    nota = Decimal(calificacion_value)
                    if nota < 0 or nota > 10:
                        messages.warning(request, f'⚠️ La nota para {nombre_aporte} debe estar entre 0 y 10')
                        continue
                    codigo = nombre_aporte.upper().replace(' ', '_')[:50]
                    tipo_aporte, created = TipoAporte.objects.get_or_create(
                        codigo=codigo,
                        defaults={'nombre': nombre_aporte, 'peso': 1.0, 'orden': 0, 'activo': True}
                    )
                    if not created and tipo_aporte.nombre != nombre_aporte:
                        tipo_aporte.nombre = nombre_aporte
                        tipo_aporte.save()
                    observaciones_completas = f"{observaciones_generales}\n{obs_aporte}".strip()
                    CalificacionParcial.objects.update_or_create(
                        student=student,
                        subject=subject,
                        parcial=parcial,
                        quimestre=quimestre,
                        tipo_aporte=tipo_aporte,
                        defaults={'calificacion': nota, 'observaciones': observaciones_completas, 'registrado_por': teacher}
                    )
                    calificaciones_guardadas += 1
                except Exception:
                    messages.warning(request, f'⚠️ Valor inválido para {nombre_aporte}: {calificacion_value}')

        # 2) Asistencia
        att_status = request.POST.get('att_status')
        att_notes = request.POST.get('att_notes', '')
        if att_status:
            Attendance.objects.update_or_create(
                student=student,
                date=fecha,
                defaults={'status': att_status, 'notes': att_notes}
            )

        # 3) Informe (Activity)
        rep_performance = request.POST.get('rep_performance', 'Bueno')
        rep_topics = request.POST.get('rep_topics', '')
        rep_techniques = request.POST.get('rep_techniques', '')
        rep_pieces = request.POST.get('rep_pieces', '')
        rep_observations = request.POST.get('rep_observations', '')
        rep_practice_time = request.POST.get('rep_practice_time')
        rep_strengths = request.POST.get('rep_strengths', '')
        rep_areas_to_improve = request.POST.get('rep_areas_to_improve', '')
        rep_homework = request.POST.get('rep_homework', '')
        if any([rep_topics, rep_techniques, rep_pieces, rep_observations, rep_strengths, rep_areas_to_improve, rep_homework, rep_practice_time]):
            clase = Clase.objects.filter(teacher=teacher, subject=subject).first()
            if not clase:
                clase = Clase.objects.create(
                    teacher=teacher,
                    name=f"{subject} - {teacher.full_name}",
                    subject=subject,
                    description='Clase auto-creada para informes desde dashboard',
                    active=True
                )
            activity = Activity(
                student=student,
                clase=clase,
                subject=subject,
                class_number=0,
                date=fecha,
                topics_worked=rep_topics,
                techniques=rep_techniques,
                pieces=rep_pieces,
                performance=rep_performance,
                observations=rep_observations,
                strengths=rep_strengths,
                areas_to_improve=rep_areas_to_improve,
                homework=rep_homework
            )
            # práctica: validar rango si viene
            try:
                if rep_practice_time is not None and str(rep_practice_time).strip() != '':
                    pt_int = int(rep_practice_time)
                    if 15 <= pt_int <= 180:
                        activity.practice_time = pt_int
            except Exception:
                pass
            activity.save()

        if calificaciones_guardadas > 0:
            promedio_parcial = CalificacionParcial.calcular_promedio_parcial(student, subject, parcial, quimestre)
            messages.success(request, f'✅ Guardado unificado para {student.name}. Calificaciones: {calificaciones_guardadas}. Promedio parcial: <strong>{promedio_parcial}</strong>')
        else:
            messages.success(request, f'✅ Asistencia e informe guardados para {student.name}')

    except Exception as e:
        messages.error(request, f'❌ Error en guardado unificado: {e}')
    return redirect('teachers:teacher_dashboard')
@login_required
@teacher_required
def obtener_calificaciones_estudiante(request, student_id):
    """
    Vista AJAX para obtener calificaciones existentes de un estudiante
    Para pre-llenar el formulario
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Solo peticiones AJAX'}, status=400)
    
    teacher = request.user.teacher_profile
    subject = request.GET.get('subject')
    parcial = request.GET.get('parcial', '1P')
    quimestre = request.GET.get('quimestre', 'Q1')
    
    try:
        student = get_object_or_404(
            Student,
            id=student_id,
            teacher=teacher,
            active=True
        )
        
        # Obtener calificaciones existentes
        calificaciones = CalificacionParcial.objects.filter(
            student=student,
            subject=subject,
            parcial=parcial,
            quimestre=quimestre
        ).select_related('tipo_aporte')
        
        # Calcular promedio
        promedio = CalificacionParcial.calcular_promedio_parcial(
            student, subject, parcial, quimestre
        )
        
        data = {
            'calificaciones': [
                {
                    'tipo_aporte_id': c.tipo_aporte.id,
                    'tipo_aporte_nombre': c.tipo_aporte.nombre,
                    'calificacion': float(c.calificacion),
                    'observaciones': c.observaciones,
                    'fecha': c.fecha_actualizacion.strftime('%d/%m/%Y')
                }
                for c in calificaciones
            ],
            'promedio': float(promedio),
            'total_calificaciones': calificaciones.count()
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@teacher_required
def ver_libreta_estudiante(request, student_id):
    """Vista para ver la libreta completa de un estudiante"""
    teacher = request.user.teacher_profile
    
    student = get_object_or_404(
        Student,
        id=student_id,
        teacher=teacher
    )
    
    # Obtener libreta completa
    libreta = CalificacionParcial.obtener_libreta_completa(student)
    
    context = {
        'student': student,
        'libreta': libreta,
        'teacher': teacher,
    }
    
    return render(request, 'teachers/libreta_estudiante.html', context)


@login_required
@teacher_required
def gestionar_tipos_aportes(request):
    """Vista para ver y gestionar los tipos de aportes"""
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'crear_aporte':
            nombre = request.POST.get('nombre', '').strip()
            peso = request.POST.get('peso', '1.0')
            
            if nombre:
                codigo = nombre.upper().replace(' ', '_')[:50]
                
                try:
                    tipo_aporte, created = TipoAporte.objects.get_or_create(
                        codigo=codigo,
                        defaults={
                            'nombre': nombre,
                            'peso': Decimal(peso),
                            'activo': True
                        }
                    )
                    
                    if created:
                        messages.success(request, f'✅ Tipo de aporte "{nombre}" creado correctamente')
                    else:
                        messages.info(request, f'ℹ️ El tipo de aporte "{nombre}" ya existe')
                        
                except Exception as e:
                    messages.error(request, f'❌ Error al crear aporte: {str(e)}')
            
            return redirect('teachers:gestionar_aportes')
        
        elif action == 'editar_aporte':
            aporte_id = request.POST.get('aporte_id')
            nombre = request.POST.get('nombre', '').strip()
            peso = request.POST.get('peso', '1.0')
            activo = request.POST.get('activo') == 'on'
            
            try:
                aporte = get_object_or_404(TipoAporte, id=aporte_id)
                aporte.nombre = nombre
                aporte.peso = Decimal(peso)
                aporte.activo = activo
                aporte.save()
                
                messages.success(request, f'✅ Aporte "{nombre}" actualizado correctamente')
            except Exception as e:
                messages.error(request, f'❌ Error al actualizar: {str(e)}')
            
            return redirect('teachers:gestionar_aportes')
        
        elif action == 'eliminar_aporte':
            aporte_id = request.POST.get('aporte_id')
            
            try:
                aporte = get_object_or_404(TipoAporte, id=aporte_id)
                
                # Verificar si tiene calificaciones asociadas
                calificaciones_count = CalificacionParcial.objects.filter(
                    tipo_aporte=aporte
                ).count()
                
                if calificaciones_count > 0:
                    messages.warning(
                        request,
                        f'⚠️ No se puede eliminar "{aporte.nombre}" porque tiene {calificaciones_count} calificación(es) asociada(s). Puedes desactivarlo en su lugar.'
                    )
                else:
                    nombre = aporte.nombre
                    aporte.delete()
                    messages.success(request, f'🗑️ Aporte "{nombre}" eliminado correctamente')
                    
            except Exception as e:
                messages.error(request, f'❌ Error al eliminar: {str(e)}')
            
            return redirect('teachers:gestionar_aportes')
    
    # GET request
    tipos_aportes = TipoAporte.objects.all().order_by('-activo', 'nombre')
    
    # Estadísticas de uso
    aportes_con_stats = []
    for tipo in tipos_aportes:
        uso_count = CalificacionParcial.objects.filter(tipo_aporte=tipo).count()
        aportes_con_stats.append({
            'tipo': tipo,
            'uso_count': uso_count,
            'usado': uso_count > 0
        })
    
    context = {
        'teacher': teacher,
        'aportes_con_stats': aportes_con_stats,
        'total_aportes': tipos_aportes.count(),
        'aportes_activos': tipos_aportes.filter(activo=True).count(),
    }
    
    return render(request, 'teachers/gestionar_aportes.html', context)



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
    
    # Opciones dinámicas de grados
    grade_choices = list(students.values_list('grade', flat=True).distinct())
    
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
        'grade_choices': grade_choices,
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


@teacher_required
def calificaciones_detalladas_view(request):
    """Vista mejorada de calificaciones por parciales"""
    teacher = request.user.teacher_profile
    
    # Filtros
    student_id = request.GET.get('student')
    subject = request.GET.get('subject')
    parcial = request.GET.get('parcial', '1P')
    
    # Obtener estudiantes y tipos de aportes
    estudiantes = teacher.students.filter(active=True).order_by('name')
    from classes.models import TipoAporte, CalificacionParcial
    tipos_aportes = TipoAporte.objects.filter(activo=True)
    
    # Filtrar estudiantes si es necesario
    if student_id:
        estudiantes = estudiantes.filter(id=student_id)
    
    # Preparar datos para la tabla
    datos_tabla = []
    for estudiante in estudiantes:
        fila = {
            'estudiante': estudiante,
            'aportes': {},
            'promedio': 0
        }
        
        # Obtener calificaciones de cada aporte
        for tipo in tipos_aportes:
            from classes.models import get_all_subjects
            subjects_list = get_all_subjects()
            default_subject = subjects_list[0] if subjects_list else subject
            calif = CalificacionParcial.objects.filter(
                student=estudiante,
                subject=subject or default_subject,
                parcial=parcial,
                tipo_aporte=tipo
            ).first()
            
            fila['aportes'][tipo.codigo] = calif.calificacion if calif else 0
        
        # Calcular promedio
        from classes.models import get_all_subjects
        subjects_list = get_all_subjects()
        default_subject = subjects_list[0] if subjects_list else subject
        fila['promedio'] = CalificacionParcial.calcular_promedio_parcial(
            estudiante, 
            subject or default_subject, 
            parcial
        )
        
        datos_tabla.append(fila)
    
    # Estadísticas
    total_estudiantes = len(datos_tabla)
    aprobados = sum(1 for d in datos_tabla if d['promedio'] >= 7)
    en_riesgo = sum(1 for d in datos_tabla if 4 <= d['promedio'] < 7)
    reprobados = sum(1 for d in datos_tabla if d['promedio'] < 4)
    promedio_general = sum(d['promedio'] for d in datos_tabla) / total_estudiantes if total_estudiantes > 0 else 0
    
    context = {
        'datos_tabla': datos_tabla,
        'tipos_aportes': tipos_aportes,
        'parcial_actual': parcial,
        'subject_actual': subject,
        'estudiantes_lista': estudiantes,
        'materias': [(s, s) for s in get_all_subjects()],
        'estadisticas': {
            'total': total_estudiantes,
            'aprobados': aprobados,
            'en_riesgo': en_riesgo,
            'reprobados': reprobados,
            'promedio_general': round(promedio_general, 2)
        }
    }
    
    return render(request, 'teachers/calificaciones_detalladas.html', context)


@teacher_required  
def guardar_calificacion_parcial(request):
    """API para guardar calificación individual"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        from classes.models import CalificacionParcial, TipoAporte
        
        try:
            calif, created = CalificacionParcial.objects.update_or_create(
                student_id=data['student_id'],
                subject=data['subject'],
                parcial=data['parcial'],
                tipo_aporte_id=data['tipo_aporte_id'],
                defaults={'calificacion': data['calificacion']}
            )
            
            # Recalcular promedio
            promedio = CalificacionParcial.calcular_promedio_parcial(
                calif.student, calif.subject, calif.parcial
            )
            
            return JsonResponse({
                'success': True,
                'promedio': promedio,
                'message': 'Calificación guardada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ============================================
# CALIFICACIONES (CRUD)
# ============================================

@teacher_required
def grade_edit_view(request, grade_id):
    """Editar una calificación existente"""
    teacher = request.user.teacher_profile
    grade = get_object_or_404(Grade, id=grade_id, student__teacher=teacher)

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Calificación actualizada')
            return redirect('teachers:student_detail', student_id=grade.student.id)
    else:
        form = GradeForm(instance=grade, teacher=teacher)

    return render(request, 'teachers/grade_edit.html', {
        'form': form,
        'grade': grade,
    })


@teacher_required
def grade_delete_view(request, grade_id):
    """Eliminar una calificación (confirmación)"""
    teacher = request.user.teacher_profile
    grade = get_object_or_404(Grade, id=grade_id, student__teacher=teacher)

    if request.method == 'POST':
        student_id = grade.student.id
        grade.delete()
        messages.success(request, 'Calificación eliminada')
        return redirect('teachers:student_detail', student_id=student_id)

    return render(request, 'teachers/grade_confirm_delete.html', {
        'grade': grade,
    })

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
# API ESTADÍSTICAS
# ============================================

@login_required
@teacher_required
def api_estadisticas(request):
    teacher = request.user.teacher_profile
    estudiantes = teacher.students.filter(active=True)
    datos = []
    for est in estudiantes:
        datos.append({
            'name': est.name,
            'promedio': float(CalificacionParcial.calcular_promedio_general(est)),
            'materias': []
        })
    return JsonResponse({'estudiantes': datos})


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
    """Enviar calificaciones por email (texto simple)"""
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


@login_required
@teacher_required
def send_student_report_email(request, student_id):
    """Enviar el reporte HTML unificado de calificaciones al email del representante"""
    teacher = request.user.teacher_profile
    student = get_object_or_404(Student, id=student_id, teacher=teacher)
    if not student.parent_email:
        messages.error(request, 'Este estudiante no tiene email registrado')
        return redirect('teachers:informes')
    from utils.notifications import NotificacionEmail
    ok = NotificacionEmail.enviar_reporte_calificaciones(student, student.parent_email)
    if ok:
        messages.success(request, f'✅ Reporte enviado a {student.parent_email}')
    else:
        messages.error(request, '❌ No se pudo enviar el reporte')
    return redirect('teachers:informes')


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




# ============================================
# DEBERES
# ============================================

@login_required
def dashboard_profesor(request):
    """Dashboard principal para profesores"""
    if not teacher_required(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('home')

    # Deberes recientes (últimos 5)
    deberes_recientes = Deber.objects.filter(
        profesor=request.user
    ).select_related('materia').order_by('fecha_asignacion')[:5]
    
    # Entregas recientes (últimas 10)
    entregas_recientes = DeberEntrega.objects.filter(
        deber__profesor=request.user,
        estado__in=['entregado', 'tarde']
    ).select_related('estudiante', 'deber').order_by('-fecha_entrega')[:10]
    
    # Deberes próximos a vencer (próximos 7 días)
    fecha_limite = timezone.now() + timedelta(days=7)
    deberes_proximos = Deber.objects.filter(
        profesor=request.user,
        estado='activo',
        fecha_entrega__gte=timezone.now(),
        fecha_entrega__lte=fecha_limite
    ).order_by('fecha_entrega')[:5]
    
    # Estadísticas por materia
    estadisticas_materias = Clase.objects.filter(
        profesor=request.user
    ).annotate(
        total_deberes=Count('deberes'),
        deberes_activos_count=Count('deberes', filter=Q(deberes__estado='activo'))
    ).order_by('-total_deberes')[:5]
    
    # Promedio de calificaciones por materia
    promedios_materias = []
    for materia in estadisticas_materias:
        promedio = DeberEntrega.objects.filter(
            deber__materia=materia,
            calificacion__isnull=False
        ).aggregate(Avg('calificacion'))['calificacion__avg']
        
        promedios_materias.append({
            'materia': materia,
            'promedio': round(promedio, 2) if promedio else 0
        })
    
    # Gráfico de entregas por estado
    estados_entregas = DeberEntrega.objects.filter(
        deber__profesor=request.user
    ).values('estado').annotate(total=Count('id'))
    
    deberes = Deber.objects.filter(profesor=request.user)
    total_deberes = deberes.count()

    deberes_activos = deberes.filter(estado='activo').count()

    total_estudiantes = User.objects.filter(
        Q(cursos_estudiante__materias__profesor=request.user) |
        Q(deberes_asignados__profesor=request.user)
    ).distinct().count()

    entregas_pendientes = DeberEntrega.objects.filter(
        deber__profesor=request.user,
        estado='entregado'
    ).count()
    
    context = {
        'total_deberes': total_deberes,
        'deberes_activos': deberes_activos,
        'total_estudiantes': total_estudiantes,
        'entregas_pendientes': entregas_pendientes,
        'deberes_recientes': deberes_recientes,
        'entregas_recientes': entregas_recientes,
        'deberes_proximos': deberes_proximos,
        'estadisticas_materias': estadisticas_materias,
        'promedios_materias': promedios_materias,
        'estados_entregas': estados_entregas,
    }
    
    return render(request, 'teachers/dashboard_profesor.html', context)


@login_required
def dashboard_estudiante(request):
    """Dashboard principal para estudiantes"""
    if not student_required(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('home')
    
    # Obtener todos los deberes del estudiante
    todos_deberes = Deber.objects.filter(
        Q(cursos__in=request.user.cursos_estudiante.all()) |
        Q(estudiantes_especificos=request.user),
        estado='activo'
    ).distinct()
    
    # Deberes pendientes (no entregados y no vencidos)
    deberes_pendientes = []
    deberes_vencidos = []
    deberes_proximos = []
    
    for deber in todos_deberes:
        entrega = DeberEntrega.objects.filter(
            deber=deber,
            estudiante=request.user
        ).first()
        
        if not entrega or entrega.estado == 'pendiente':
            if deber.esta_vencido():
                deberes_vencidos.append(deber)
            else:
                deberes_pendientes.append(deber)
                # Próximos 3 días
                if deber.dias_restantes() <= 3:
                    deberes_proximos.append(deber)
    
    # Estadísticas
    total_deberes = todos_deberes.count()
    total_pendientes = len(deberes_pendientes)
    total_vencidos = len(deberes_vencidos)
    
    # Entregas realizadas
    mis_entregas = DeberEntrega.objects.filter(
        estudiante=request.user,
        estado__in=['entregado', 'revisado', 'tarde']
    ).select_related('deber', 'deber__materia').order_by('-fecha_entrega')[:10]
    
    total_entregados = mis_entregas.count()
    
    # Calificaciones recientes
    calificaciones_recientes = DeberEntrega.objects.filter(
        estudiante=request.user,
        estado='revisado',
        calificacion__isnull=False
    ).select_related('deber', 'deber__materia').order_by('-fecha_actualizacion')[:5]
    
    # Promedio general
    promedio_general = DeberEntrega.objects.filter(
        estudiante=request.user,
        calificacion__isnull=False
    ).aggregate(Avg('calificacion'))['calificacion__avg']
    
    # Estadísticas por materia
    materias_stats = {}
    for entrega in DeberEntrega.objects.filter(
        estudiante=request.user,
        calificacion__isnull=False
    ).select_related('deber__materia'):
        materia_nombre = entrega.deber.materia.nombre
        if materia_nombre not in materias_stats:
            materias_stats[materia_nombre] = {
                'calificaciones': [],
                'total_puntos': 0,
                'puntos_obtenidos': 0
            }
        materias_stats[materia_nombre]['calificaciones'].append(float(entrega.calificacion))
        materias_stats[materia_nombre]['total_puntos'] += float(entrega.deber.puntos_totales)
        materias_stats[materia_nombre]['puntos_obtenidos'] += float(entrega.calificacion)
    
    # Calcular promedios por materia
    promedios_materias = []
    for materia, stats in materias_stats.items():
        promedio = sum(stats['calificaciones']) / len(stats['calificaciones'])
        porcentaje = (stats['puntos_obtenidos'] / stats['total_puntos']) * 100 if stats['total_puntos'] > 0 else 0
        promedios_materias.append({
            'materia': materia,
            'promedio': round(promedio, 2),
            'porcentaje': round(porcentaje, 1)
        })
    
    context = {
        'total_deberes': total_deberes,
        'total_pendientes': total_pendientes,
        'total_entregados': total_entregados,
        'total_vencidos': total_vencidos,
        'deberes_pendientes': deberes_pendientes[:5],
        'deberes_proximos': deberes_proximos,
        'mis_entregas': mis_entregas,
        'calificaciones_recientes': calificaciones_recientes,
        'promedio_general': round(promedio_general, 2) if promedio_general else 0,
        'promedios_materias': promedios_materias,
    }
    
    return render(request, 'teachers/dashboard_estudiante.html', context)

# ===== VISTAS PARA PROFESORES =====

@login_required
def crear_deber(request):
    """Vista para crear un nuevo deber (solo profesores)"""
    
    # Verificar que el usuario es profesor
    if not teacher_required(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('home')
    
    # Obtener la instancia de Teacher asociada al usuario logueado
    try:
        teacher_instance = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, 'No se encontró tu perfil de profesor')
        return redirect('home')

    if request.method == 'POST':
        form = DeberForm(request.POST, request.FILES, teacher=teacher_instance)
        if form.is_valid():
            deber = form.save(commit=False)
            deber.teacher = teacher_instance  # asignar el Teacher correcto
            deber.save()
            form.save_m2m()  # guardar relaciones ManyToMany
            
            messages.success(request, f'✅ Deber "{deber.titulo}" creado exitosamente')
            return redirect('lista_deberes_profesor')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = DeberForm(teacher=teacher_instance)
    
    context = {
        'form': form,
        'titulo': 'Crear Nuevo Deber'
    }
    return render(request, 'teachers/deberes/crear_deber.html', context)


@login_required
def editar_deber(request, deber_id):
    """Vista para editar un deber existente"""
    deber = get_object_or_404(Deber, id=deber_id, profesor=request.user)
    
    if request.method == 'POST':
        form = DeberForm(request.POST, request.FILES, instance=deber, profesor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Deber "{deber.titulo}" actualizado exitosamente')
            return redirect('lista_deberes_profesor')
    else:
        form = DeberForm(instance=deber, profesor=request.user)
    
    context = {
        'form': form,
        'deber': deber, 
        'titulo': 'Editar Deber'
    }
    return render(request, 'teachers/deberes/crear_deber.html', context)

@login_required
def eliminar_deber(request, deber_id):
    """Vista para eliminar un deber"""
    deber = get_object_or_404(Deber, id=deber_id, profesor=request.user)
    
    if request.method == 'POST':
        titulo = deber.titulo
        deber.delete()
        messages.success(request, f'🗑️ Deber "{titulo}" eliminado exitosamente')
        return redirect('lista_deberes_profesor')
    
    context = {'deber': deber}
    return render(request, 'teachers/deberes/confirmar_eliminar.html', context)

@login_required
def lista_deberes_profesor(request):
    """Vista para listar todos los deberes del profesor"""
    if not teacher_required(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('home')
    # Obtener el objeto Teacher vinculado al usuario logueado
    teacher_instance = Teacher.objects.get(user=request.user)

    # Filtros
    estado_filtro = request.GET.get('estado', 'todos')
    materia_filtro = request.GET.get('materia', 'todas')
    
    # Query base
    deberes = Deber.objects.filter(teacher=request.user).select_related('clase')
    
    # Aplicar filtros
    if estado_filtro != 'todos':
        deberes = deberes.filter(estado=estado_filtro)
    
    if materia_filtro != 'todas':
        deberes = deberes.filter(materia_id=materia_filtro)
    
    # Agregar estadísticas
    deberes = deberes.annotate(
        total_entregas=Count('entregas'),
        entregas_revisadas=Count('entregas', filter=Q(entregas__estado='revisado'))
    )
    
    # Estadísticas generales
    total_deberes = Deber.objects.filter(teacher=request.user).count()
    deberes_activos = Deber.objects.filter(teacher=request.user, estado='activo').count()
    total_entregas_pendientes = DeberEntrega.objects.filter(
        deber__teacher=request.user,
        estado='entregado'
    ).count()
    
    # Obtener materias para el filtro
    clase = Clase.objects.filter(teacher=request.user.teacher_profile)

    context = {
        'deberes': deberes,
        'total_deberes': total_deberes,
        'deberes_activos': deberes_activos,
        'total_entregas_pendientes': total_entregas_pendientes,
        'clase': clase,
        'estado_filtro': estado_filtro,
        'materia_filtro': materia_filtro,
    }
    return render(request, 'teachers/deberes/lista_deberes_profesor.html', context)

@login_required
def ver_entregas(request, deber_id):
    """Vista para ver todas las entregas de un deber"""
    deber = get_object_or_404(Deber, id=deber_id, profesor=request.user)
    
    # Obtener todos los estudiantes que deberían entregar
    estudiantes_curso = User.objects.filter(cursos_estudiante__in=deber.cursos.all())
    todos_estudiantes = (estudiantes_curso | deber.estudiantes_especificos.all()).distinct()
    
    # Obtener entregas existentes
    entregas = DeberEntrega.objects.filter(deber=deber).select_related('estudiante')
    
    # Crear lista con estado de cada estudiante
    lista_estudiantes = []
    for estudiante in todos_estudiantes:
        entrega = entregas.filter(estudiante=estudiante).first()
        lista_estudiantes.append({
            'estudiante': estudiante,
            'entrega': entrega,
            'tiene_entrega': entrega is not None,
        })
    
    # Ordenar: primero los que entregaron
    lista_estudiantes.sort(key=lambda x: (not x['tiene_entrega'], x['estudiante'].last_name))
    
    # Filtro de estado
    estado_filtro = request.GET.get('estado', 'todos')
    if estado_filtro == 'entregados':
        lista_estudiantes = [e for e in lista_estudiantes if e['tiene_entrega']]
    elif estado_filtro == 'pendientes':
        lista_estudiantes = [e for e in lista_estudiantes if not e['tiene_entrega']]
    
    context = {
        'deber': deber,
        'lista_estudiantes': lista_estudiantes,
        'total_estudiantes': todos_estudiantes.count(),
        'total_entregados': entregas.filter(estado__in=['entregado', 'revisado', 'tarde']).count(),
        'estado_filtro': estado_filtro,
    }
    return render(request, 'teachers/deberes/ver_entregas.html', context)

@login_required
def calificar_entrega(request, entrega_id):
    """Vista para calificar una entrega"""
    entrega = get_object_or_404(DeberEntrega, id=entrega_id)
    
    # Verificar que el profesor sea el dueño del deber
    if entrega.deber.profesor != request.user:
        return HttpResponseForbidden("No tienes permisos para calificar esta entrega")
    
    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=entrega)
        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.estado = 'revisado'
            entrega.save()
            
            messages.success(request, f'✅ Entrega de {entrega.estudiante.get_full_name()} calificada exitosamente')
            return redirect('ver_entregas', deber_id=entrega.deber.id)
    else:
        form = CalificacionForm(instance=entrega)
    
    context = {
        'form': form,
        'entrega': entrega,
    }
    return render(request, 'teachers/deberes/calificar_entrega.html', context)

# ===== VISTAS PARA ESTUDIANTES =====

@login_required
def mis_deberes(request):
    """Vista para que los estudiantes vean sus deberes asignados"""
    if not student_required(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('home')
    
    # Obtener deberes asignados al estudiante
    deberes = Deber.objects.filter(
        Q(cursos__in=request.user.cursos_estudiante.all()) |
        Q(estudiantes_especificos=request.user),
        estado='activo'
    ).distinct().select_related('materia', 'profesor').prefetch_related(
        Prefetch('entregas', queryset=DeberEntrega.objects.filter(estudiante=request.user))
    )
    
    # Agregar información de entrega para cada deber
    deberes_con_estado = []
    for deber in deberes:
        entrega = deber.entregas.first() if deber.entregas.exists() else None
        
        deberes_con_estado.append({
            'deber': deber,
            'entrega': entrega,
            'esta_vencido': deber.esta_vencido(),
            'tiene_entrega': entrega is not None,
            'dias_restantes': deber.dias_restantes(),
        })
    
    # Separar por categorías
    pendientes = [d for d in deberes_con_estado if not d['tiene_entrega'] and not d['esta_vencido']]
    entregados = [d for d in deberes_con_estado if d['tiene_entrega']]
    vencidos = [d for d in deberes_con_estado if not d['tiene_entrega'] and d['esta_vencido']]
    
    # Ordenar por fecha de entrega
    pendientes.sort(key=lambda x: x['deber'].fecha_entrega)
    
    context = {
        'pendientes': pendientes,
        'entregados': entregados,
        'vencidos': vencidos,
        'total_pendientes': len(pendientes),
        'total_entregados': len(entregados),
    }
    return render(request, 'teachers/deberes/mis_deberes.html', context)

@login_required
def entregar_deber(request, deber_id):
    """Vista para que el estudiante entregue un deber"""
    from django.contrib.auth.models import User
    
    deber = get_object_or_404(Deber, id=deber_id)
    
    # Verificar que el estudiante tenga acceso a este deber
    tiene_acceso = (
        request.user.cursos_estudiante.filter(deberes=deber).exists() or
        deber.estudiantes_especificos.filter(id=request.user.id).exists()
    )
    
    if not tiene_acceso:
        messages.error(request, 'No tienes acceso a este deber')
        return redirect('mis_deberes')
    
    # Verificar si ya existe una entrega
    entrega, created = DeberEntrega.objects.get_or_create(
        deber=deber,
        estudiante=request.user,
        defaults={'estado': 'pendiente'}
    )
    
    # No permitir reenvío si ya está revisado
    if entrega.estado == 'revisado' and not created:
        messages.warning(request, 'Este deber ya ha sido calificado y no se puede modificar')
        return redirect('mis_deberes')
    
    if request.method == 'POST':
        form = DeberEntregaForm(request.POST, request.FILES, instance=entrega)
        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.estado = 'entregado'
            entrega.save()
            
            messages.success(request, '✅ Deber entregado exitosamente')
            return redirect('mis_deberes')
    else:
        form = DeberEntregaForm(instance=entrega)
    
    context = {
        'form': form,
        'deber': deber,
        'entrega': entrega,
        'puede_entregar': not deber.esta_vencido() or entrega.estado == 'pendiente',
    }
    return render(request, 'teachers/deberes/entregar_deber.html', context)

@login_required
def detalle_deber(request, deber_id):
    """Vista para ver los detalles de un deber"""
    deber = get_object_or_404(Deber, id=deber_id)
    
    # Verificar acceso
    if teacher_required(request.user):
        if deber.profesor != request.user:
            return HttpResponseForbidden("No tienes acceso a este deber")
    elif student_required(request.user):
        tiene_acceso = (
            request.user.cursos_estudiante.filter(deberes=deber).exists() or
            deber.estudiantes_especificos.filter(id=request.user.id).exists()
        )
        if not tiene_acceso:
            return HttpResponseForbidden("No tienes acceso a este deber")
    
    # Obtener entrega si es estudiante
    entrega = None
    if student_required(request.user):
        entrega = DeberEntrega.objects.filter(deber=deber, estudiante=request.user).first()
    
    context = {
        'deber': deber,
        'entrega': entrega,
        'es_profesor': teacher_required(request.user),
    }
    return render(request, 'teachers/deberes/detalle_deber.html', context)