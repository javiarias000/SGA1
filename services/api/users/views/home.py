# users/views/home.py
from datetime import date
from django.shortcuts import render


def home_view(request):
    from matriculas.malla_curricular import (
        ASIGNATURAS_COMUNES,
        MODULOS_FORMATIVOS,
        ASIGNATURAS_COMPLEMENTARIAS,
        INSTRUMENTOS,
    )

    # Total horas por año (columnas 1-11) sumando todas las asignaturas comunes
    totales_comunes = []
    for anio_idx in range(11):
        total = sum(
            s['horas'][anio_idx]
            for s in ASIGNATURAS_COMUNES
            if s.get('horas') and len(s['horas']) > anio_idx
        )
        totales_comunes.append(total)

    today = date.today()
    ciclo_actual = f"{today.year}-{today.year + 1}"

    try:
        from students.models import Student
        total_students = Student.objects.count()
    except Exception:
        total_students = 0

    return render(request, 'home.html', {
        'malla_comunes': ASIGNATURAS_COMUNES,
        'malla_modulos': MODULOS_FORMATIVOS,
        'malla_complementarias': ASIGNATURAS_COMPLEMENTARIAS,
        'totales_comunes': totales_comunes,
        'instrumentos_lista': INSTRUMENTOS,
        'ciclo_actual': ciclo_actual,
        'total_students': total_students,
    })
