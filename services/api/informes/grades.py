"""
Calcula los datos de calificaciones y asistencias para informes,
leyendo desde la base de datos del SGA1 (equivalente al sistema de
lectura de Google Sheets del informe-whatsapp).
"""
from decimal import Decimal
from django.db.models import Avg, Count, Q


# ── Mapa de escala cualitativa (sistema Ecuador) ──────────────────────────────
def get_escala(nota: float) -> str:
    if nota >= 9:
        return 'DAR'
    elif nota >= 7:
        return 'AAR'
    elif nota >= 4.01:
        return 'PAAR'
    return 'NAAR'


# ── Parciales (1P / 2P / 3P / 4P) ────────────────────────────────────────────
def get_grades_parcial(grade_level_id: int, subject_id: int, parcial: str,
                       ciclo: str = '2025-2026') -> list[dict]:
    """
    Devuelve lista de estudiantes con su promedio ponderado del parcial.
    parcial ∈ {'1P','2P','3P','4P'}
    """
    from classes.models import CalificacionParcial, Enrollment
    from students.models import Student

    # Quimestre basado en el parcial
    quimestre = 'Q1' if parcial in ('1P', '2P') else 'Q2'

    students = Student.objects.filter(
        grade_level_id=grade_level_id,
        active=True,
    ).select_related('usuario', 'grade_level')

    result = []
    for st in students:
        cals = CalificacionParcial.objects.filter(
            student=st,
            subject_id=subject_id,
            parcial=parcial,
            quimestre=quimestre,
        ).select_related('tipo_aporte')

        if not cals.exists():
            continue

        pesos = sum(float(c.tipo_aporte.peso) for c in cals)
        if pesos == 0:
            nota = 0.0
        else:
            nota = sum(
                float(c.calificacion) * float(c.tipo_aporte.peso) for c in cals
            ) / pesos

        nota = round(nota, 2)
        telefono = getattr(st, 'parent_phone', '') or ''

        result.append({
            'nombre': st.usuario.nombre if st.usuario else '—',
            'curso': str(st.grade_level) if st.grade_level else '—',
            'telefono_representante': telefono,
            'nota': nota,
            'escala_cualitativa': get_escala(nota),
            'estado': 'DIFICULTAD' if nota < 7 else 'APROBADO',
            'faltas_justificadas': 0,
            'faltas_injustificadas': 0,
            'student_id': st.pk,
        })

    return result


# ── Quimestres (1Q / 2Q) ─────────────────────────────────────────────────────
def get_grades_quimestre(grade_level_id: int, subject_id: int, quimestre_code: str,
                         ciclo: str = '2025-2026') -> list[dict]:
    """
    Calcula la nota quimestral: promedio ponderado de parciales (70%) + examen (30%).
    quimestre_code ∈ {'1Q','2Q'}
    """
    from classes.models import CalificacionParcial, TipoAporte, Asistencia, Enrollment
    from students.models import Student

    quimestre = 'Q1' if quimestre_code == '1Q' else 'Q2'
    parciales_del_q = ('1P', '2P') if quimestre == 'Q1' else ('3P', '4P')

    students = Student.objects.filter(
        grade_level_id=grade_level_id,
        active=True,
    ).select_related('usuario', 'grade_level')

    result = []
    for st in students:
        # Promedio de parciales (70%)
        promedios_parciales = []
        for parc in parciales_del_q:
            cals = CalificacionParcial.objects.filter(
                student=st, subject_id=subject_id,
                parcial=parc, quimestre=quimestre,
            ).select_related('tipo_aporte')
            if cals.exists():
                pesos = sum(float(c.tipo_aporte.peso) for c in cals)
                if pesos:
                    promedio = sum(
                        float(c.calificacion) * float(c.tipo_aporte.peso) for c in cals
                    ) / pesos
                    promedios_parciales.append(round(promedio, 2))

        if not promedios_parciales:
            continue

        prom_parciales = round(sum(promedios_parciales) / len(promedios_parciales), 2)

        # Nota de examen quimestral (tipo_aporte llamado 'Examen' o similar)
        examen_cal = CalificacionParcial.objects.filter(
            student=st, subject_id=subject_id,
            quimestre=quimestre,
            tipo_aporte__nombre__icontains='examen',
        ).first()
        examen_nota = float(examen_cal.calificacion) if examen_cal else None

        # Nota final = 70% parciales + 30% examen
        if examen_nota is not None:
            nota_final = round(prom_parciales * 0.7 + examen_nota * 0.3, 2)
        else:
            nota_final = prom_parciales  # sin examen registrado

        # Faltas del quimestre vía Enrollment → Asistencia
        faltas_j = faltas_i = 0
        if st.usuario:
            enrollments = Enrollment.objects.filter(
                estudiante=st.usuario,
                clase__subject_id=subject_id,
                clase__ciclo_lectivo=ciclo,
            )
            for enr in enrollments:
                faltas_j += enr.asistencias.filter(estado='Justificado').count()
                faltas_i += enr.asistencias.filter(estado='Ausente').count()

        telefono = getattr(st, 'parent_phone', '') or ''
        result.append({
            'nombre': st.usuario.nombre if st.usuario else '—',
            'curso': str(st.grade_level) if st.grade_level else '—',
            'telefono_representante': telefono,
            'nota': nota_final,
            'p1': promedios_parciales[0] if len(promedios_parciales) > 0 else None,
            'p2': promedios_parciales[1] if len(promedios_parciales) > 1 else None,
            'prom_parciales': prom_parciales,
            'examen': examen_nota,
            'escala_cualitativa': get_escala(nota_final),
            'estado': 'DIFICULTAD' if nota_final < 7 else 'APROBADO',
            'faltas_justificadas': faltas_j,
            'faltas_injustificadas': faltas_i,
            'student_id': st.pk,
        })

    return result


# ── Anual ─────────────────────────────────────────────────────────────────────
def get_grades_anual(grade_level_id: int, subject_id: int,
                     ciclo: str = '2025-2026') -> list[dict]:
    """Nota anual = 80% promedio quimestral + 20% evaluación final."""
    q1_list = {s['student_id']: s for s in get_grades_quimestre(grade_level_id, subject_id, '1Q', ciclo)}
    q2_list = {s['student_id']: s for s in get_grades_quimestre(grade_level_id, subject_id, '2Q', ciclo)}

    all_ids = set(q1_list) | set(q2_list)
    result = []

    for sid in all_ids:
        q1_data = q1_list.get(sid, {})
        q2_data = q2_list.get(sid, {})
        q1_nota = q1_data.get('nota', 0.0)
        q2_nota = q2_data.get('nota', 0.0)

        # Promedio de quimestres
        if q1_data and q2_data:
            prom_q = round((q1_nota + q2_nota) / 2, 2)
        elif q1_data:
            prom_q = q1_nota
        else:
            prom_q = q2_nota

        # Nota final anual (sin evaluación final por ahora; puede extenderse)
        nota_final = round(prom_q * 0.8, 2)

        base = q1_data or q2_data
        result.append({
            'nombre': base.get('nombre', '—'),
            'curso': base.get('curso', '—'),
            'telefono_representante': base.get('telefono_representante', ''),
            'nota': nota_final,
            'q1': q1_nota,
            'q2': q2_nota,
            'escala_cualitativa': get_escala(nota_final),
            'estado': 'DIFICULTAD' if nota_final < 7 else 'APROBADO',
            'faltas_justificadas': base.get('faltas_justificadas', 0),
            'faltas_injustificadas': base.get('faltas_injustificadas', 0),
            'student_id': sid,
        })

    return result


# ── Asistencias (A1 / A2 / A3 / A4) ──────────────────────────────────────────
def get_grades_asistencia(grade_level_id: int, subject_id: int, registro: str,
                          ciclo: str = '2025-2026') -> list[dict]:
    """
    Agrega asistencias por período (A1-A4 ~ parciales 1P-4P).
    registro ∈ {'A1','A2','A3','A4'}
    """
    from classes.models import Asistencia, Enrollment
    from students.models import Student
    import datetime

    # Mapa A1-A4 → parcial de referencia para filtrar por fecha aproximada
    # Como SGA1 no tiene rango de fechas por parcial, cuenta todas las asistencias
    # del enrollment. Se puede refinar con fechas si se agrega ese campo.
    parcial_map = {'A1': 'Q1', 'A2': 'Q1', 'A3': 'Q2', 'A4': 'Q2'}

    students = Student.objects.filter(
        grade_level_id=grade_level_id,
        active=True,
    ).select_related('usuario', 'grade_level')

    result = []
    for st in students:
        if not st.usuario:
            continue
        enrollments = Enrollment.objects.filter(
            estudiante=st.usuario,
            clase__subject_id=subject_id,
            clase__ciclo_lectivo=ciclo,
        )

        total = asistencias = faltas_j = faltas_i = 0
        for enr in enrollments:
            asis_qs = enr.asistencias.all()
            total += asis_qs.count()
            asistencias += asis_qs.filter(estado='Presente').count()
            faltas_j += asis_qs.filter(estado='Justificado').count()
            faltas_i += asis_qs.filter(estado='Ausente').count()

        pct = round((asistencias / total * 100), 1) if total > 0 else 0.0

        if faltas_i >= 3:
            estado = 'INASISTENCIAS'
        elif pct < 75:
            estado = 'BAJO_ASISTENCIA'
        else:
            estado = 'REGULAR'

        telefono = getattr(st, 'parent_phone', '') or ''
        result.append({
            'nombre': st.usuario.nombre if st.usuario else '—',
            'curso': str(st.grade_level) if st.grade_level else '—',
            'telefono_representante': telefono,
            'asistencias': asistencias,
            'faltas_justificadas': faltas_j,
            'faltas_injustificadas': faltas_i,
            'total_clases': total,
            'pct_asistencia': pct,
            'estado': estado,
            'student_id': st.pk,
        })

    return result


# ── Dispatcher principal ──────────────────────────────────────────────────────
def get_grades(grade_level_id: int, subject_id: int, periodo: str,
               ciclo: str = '2025-2026') -> list[dict]:
    """Punto de entrada unificado. periodo ∈ {'1P'..'4P','1Q','2Q','Anual','A1'..'A4'}"""
    if periodo in ('1P', '2P', '3P', '4P'):
        return get_grades_parcial(grade_level_id, subject_id, periodo, ciclo)
    elif periodo in ('1Q', '2Q'):
        return get_grades_quimestre(grade_level_id, subject_id, periodo, ciclo)
    elif periodo == 'Anual':
        return get_grades_anual(grade_level_id, subject_id, ciclo)
    elif periodo in ('A1', 'A2', 'A3', 'A4'):
        return get_grades_asistencia(grade_level_id, subject_id, periodo, ciclo)
    return []
