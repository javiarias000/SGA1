from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Instrumento, PrestamoInstrumento
from students.models import Student
import datetime


@login_required
def lista_instrumentos_view(request):
    tipo_filtro = request.GET.get('tipo', '')
    estado_filtro = request.GET.get('estado', '')
    qs = Instrumento.objects.all()
    if tipo_filtro:
        qs = qs.filter(tipo=tipo_filtro)
    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)
    return render(request, 'inventario/lista.html', {
        'instrumentos': qs,
        'tipos': Instrumento.Tipo.choices,
        'estados': Instrumento.Estado.choices,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
    })


@login_required
def detalle_instrumento_view(request, pk):
    instrumento = get_object_or_404(Instrumento, pk=pk)
    prestamos = instrumento.prestamos.select_related('estudiante__usuario').order_by('-fecha_prestamo')[:10]
    return render(request, 'inventario/detalle.html', {
        'instrumento': instrumento, 'prestamos': prestamos,
    })


@login_required
def crear_instrumento_view(request):
    if not request.user.is_staff:
        messages.error(request, 'Sin permiso.')
        return redirect('inventario:lista')
    if request.method == 'POST':
        Instrumento.objects.create(
            nombre=request.POST.get('nombre'),
            tipo=request.POST.get('tipo', 'OTRO'),
            marca=request.POST.get('marca', ''),
            numero_serie=request.POST.get('numero_serie'),
            descripcion=request.POST.get('descripcion', ''),
            fecha_adquisicion=request.POST.get('fecha_adquisicion') or None,
        )
        messages.success(request, 'Instrumento registrado.')
        return redirect('inventario:lista')
    return render(request, 'inventario/instrumento_form.html', {'tipos': Instrumento.Tipo.choices})


@login_required
def prestamo_view(request, pk):
    instrumento = get_object_or_404(Instrumento, pk=pk)
    if instrumento.estado != 'DISPONIBLE':
        messages.error(request, 'El instrumento no está disponible.')
        return redirect('inventario:detalle', pk=pk)
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        fecha_dev = request.POST.get('fecha_devolucion_esperada')
        PrestamoInstrumento.objects.create(
            instrumento=instrumento,
            estudiante_id=student_id,
            fecha_devolucion_esperada=fecha_dev,
            observaciones=request.POST.get('observaciones', ''),
            registrado_por=request.user.usuario,
        )
        instrumento.estado = 'PRESTADO'
        instrumento.save()
        messages.success(request, 'Préstamo registrado.')
        return redirect('inventario:detalle', pk=pk)
    estudiantes = Student.objects.filter(active=True).select_related('usuario')
    return render(request, 'inventario/prestamo_form.html', {
        'instrumento': instrumento,
        'estudiantes': estudiantes,
        'fecha_min': datetime.date.today().isoformat(),
    })


@login_required
@require_POST
def devolucion_view(request, prestamo_id):
    prestamo = get_object_or_404(PrestamoInstrumento, pk=prestamo_id)
    prestamo.estado = 'DEVUELTO'
    prestamo.fecha_devolucion_real = datetime.date.today()
    prestamo.save()
    prestamo.instrumento.estado = 'DISPONIBLE'
    prestamo.instrumento.save()
    messages.success(request, 'Devolución registrada.')
    return redirect('inventario:detalle', pk=prestamo.instrumento.pk)
