"""
Reordena y agrupa el panel Django Admin siguiendo la jerarquía de datos:
  Institución → Catálogo → Personal → Académico → Evaluación → Comunicación → Sistema
"""
from django.contrib import admin

# Orden deseado por app_label (de más fundamental a más derivado)
APP_ORDER = [
    'setup',        # ⚙️  Institución (dato raíz)
    'subjects',     # 📚 Catálogo — Materias
    'classes',      # 🎓 Académico — Niveles, Clases, Matrículas, Calificaciones
    'teachers',     # 👨‍🏫 Personal — Docentes
    'students',     # 👨‍🎓 Personal — Estudiantes
    'matriculas',   # 📝 Matrículas en línea (app pública)
    'informes',     # 📊 Comunicaciones WhatsApp
    'agente',       # 🤖 Agente IA
    'users',        # 👤 Usuarios del sistema
    'auth',         # 🔑 Autenticación y permisos
    'authtoken',
    'django_celery_beat',
    'docente',
]

# Etiquetas de sección para agrupar visualmente en el template
SECTION_LABELS = {
    'setup':              ('1', '⚙️ Configuración de la Institución'),
    'subjects':           ('2', '📚 Catálogo Académico'),
    'classes':            ('2', '📚 Catálogo Académico'),
    'teachers':           ('3', '👥 Personal'),
    'students':           ('3', '👥 Personal'),
    'matriculas':         ('4', '📝 Matrículas'),
    'informes':           ('5', '📊 Comunicaciones'),
    'agente':             ('6', '🤖 Agente IA'),
    'users':              ('7', '🔑 Sistema'),
    'auth':               ('7', '🔑 Sistema'),
    'authtoken':          ('7', '🔑 Sistema'),
    'django_celery_beat': ('7', '🔑 Sistema'),
    'docente':            ('7', '🔑 Sistema'),
}


def _sort_key(app):
    label = app.get('app_label', '')
    try:
        return APP_ORDER.index(label)
    except ValueError:
        return 999


def install_custom_app_list():
    """Monkey-patch AdminSite.get_app_list to return apps in hierarchy order."""
    _original = admin.AdminSite.get_app_list

    def custom_get_app_list(self, request, app_label=None):
        app_list = _original(self, request, app_label)
        app_list.sort(key=_sort_key)
        return app_list

    admin.AdminSite.get_app_list = custom_get_app_list
