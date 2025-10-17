#!/usr/bin/env python3
"""
Script para corregir TODAS las URLs en templates de teachers y students
"""

import os
import re

def fix_teachers_urls(content):
    """Corrige todas las URLs de teachers"""
    
    # Patrón para encontrar {% url 'nombre' ... %}
    # Captura el nombre y los argumentos
    patterns = [
        # URLs sin argumentos
        (r"{%\s*url\s+'dashboard'\s*%}", "{% url 'teachers:dashboard' %}"),
        (r"{%\s*url\s+'registro'\s*%}", "{% url 'teachers:registro' %}"),
        (r"{%\s*url\s+'estudiantes'\s*%}", "{% url 'teachers:estudiantes' %}"),
        (r"{%\s*url\s+'informes'\s*%}", "{% url 'teachers:informes' %}"),
        (r"{%\s*url\s+'carpetas'\s*%}", "{% url 'teachers:carpetas' %}"),
        (r"{%\s*url\s+'grades'\s*%}", "{% url 'teachers:grades' %}"),
        (r"{%\s*url\s+'attendance'\s*%}", "{% url 'teachers:attendance' %}"),
        (r"{%\s*url\s+'profile'\s*%}", "{% url 'teachers:profile' %}"),
        (r"{%\s*url\s+'login'\s*%}", "{% url 'teachers:login' %}"),
        (r"{%\s*url\s+'logout'\s*%}", "{% url 'teachers:logout' %}"),
        (r"{%\s*url\s+'register'\s*%}", "{% url 'teachers:register' %}"),
        
        # URLs con argumentos - usar sustitución más flexible
        (r"{%\s*url\s+'student_detail'", "{% url 'teachers:student_detail'"),
        (r"{%\s*url\s+'student_edit'", "{% url 'teachers:student_edit'"),
        (r"{%\s*url\s+'student_delete'", "{% url 'teachers:student_delete'"),
        (r"{%\s*url\s+'student_code'", "{% url 'teachers:student_code'"),
        (r"{%\s*url\s+'report_card'", "{% url 'teachers:report_card'"),
        (r"{%\s*url\s+'grade_edit'", "{% url 'teachers:grade_edit'"),
        (r"{%\s*url\s+'grade_delete'", "{% url 'teachers:grade_delete'"),
        (r"{%\s*url\s+'attendance_edit'", "{% url 'teachers:attendance_edit'"),
        (r"{%\s*url\s+'attendance_delete'", "{% url 'teachers:attendance_delete'"),
        (r"{%\s*url\s+'activity_edit'", "{% url 'teachers:activity_edit'"),
        (r"{%\s*url\s+'activity_delete'", "{% url 'teachers:activity_delete'"),
        (r"{%\s*url\s+'get_class_number'", "{% url 'teachers:get_class_number'"),
        (r"{%\s*url\s+'get_student_subjects'", "{% url 'teachers:get_student_subjects'"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content


def fix_students_urls(content):
    """Corrige todas las URLs de students"""
    
    patterns = [
        # URLs sin argumentos
        (r"{%\s*url\s+'student_dashboard'\s*%}", "{% url 'students:dashboard' %}"),
        (r"{%\s*url\s+'student_login'\s*%}", "{% url 'students:login' %}"),
        (r"{%\s*url\s+'student_register'\s*%}", "{% url 'students:register' %}"),
        (r"{%\s*url\s+'student_logout'\s*%}", "{% url 'students:logout' %}"),
        (r"{%\s*url\s+'student_classes'\s*%}", "{% url 'students:classes' %}"),
        (r"{%\s*url\s+'student_grades'\s*%}", "{% url 'students:grades' %}"),
        (r"{%\s*url\s+'student_attendance'\s*%}", "{% url 'students:attendance' %}"),
        (r"{%\s*url\s+'student_profile'\s*%}", "{% url 'students:profile' %}"),
        
        # URLs con argumentos
        (r"{%\s*url\s+'student_enroll'", "{% url 'students:enroll'"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content


def fix_extends(content, app_name):
    """Corrige los extends en templates"""
    
    patterns = [
        (r"{%\s*extends\s+'base\.html'\s*%}", f"{{% extends '{app_name}/base.html' %}}"),
        (r"{%\s*extends\s+\"base\.html\"\s*%}", f"{{% extends '{app_name}/base.html' %}}"),
        (r"{%\s*extends\s+'classes/student_base\.html'\s*%}", "{% extends 'students/base.html' %}"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content


def process_file(filepath, app_name):
    """Procesa un archivo HTML"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Corregir extends
        content = fix_extends(content, app_name)
        
        # Corregir URLs según la app
        if app_name == 'teachers':
            content = fix_teachers_urls(content)
        elif app_name == 'students':
            content = fix_students_urls(content)
        
        # Guardar si hubo cambios
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corregido: {filepath}")
            return True
        else:
            print(f"⚪ Sin cambios: {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error en {filepath}: {e}")
        return False


def process_directory(directory, app_name):
    """Procesa todos los HTML en un directorio"""
    if not os.path.exists(directory):
        print(f"⚠️  No existe: {directory}")
        return 0
    
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if process_file(filepath, app_name):
                    count += 1
    
    return count


def main():
    print("🔧 Corrección Automática de URLs en Templates")
    print("=" * 60)
    print()
    
    # Verificar ubicación
    if not os.path.exists('manage.py'):
        print("❌ Ejecuta este script desde la raíz del proyecto Django")
        return
    
    # Procesar teachers
    print("📝 Procesando templates de TEACHERS...")
    teachers_dir = 'teachers/templates/teachers'
    teachers_count = process_directory(teachers_dir, 'teachers')
    print(f"✨ Teachers: {teachers_count} archivos corregidos\n")
    
    # Procesar students
    print("📝 Procesando templates de STUDENTS...")
    students_dir = 'students/templates/students'
    students_count = process_directory(students_dir, 'students')
    print(f"✨ Students: {students_count} archivos corregidos\n")
    
    print("=" * 60)
    print(f"🎉 Total: {teachers_count + students_count} archivos corregidos")
    print()
    print("⚡ Ahora recarga el servidor y prueba de nuevo")


if __name__ == '__main__':
    main()
