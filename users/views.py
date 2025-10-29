from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg

# Modelos que usas
from classes.models import Clase, Activity, Attendance

# ============================================
# DASHBOARD PRINCIPAL
# ============================================

@login_required
def dashboard(request):
    user = request.user
    if getattr(user, 'is_teacher', False):
        return redirect('teacher_dashboard')
    elif getattr(user, 'is_student', False):
        return redirect('student_dashboard')
    return render(request, 'no_permission.html', {'mensaje': 'Rol no identificado'})


