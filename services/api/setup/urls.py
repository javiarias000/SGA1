from django.urls import path
from . import views

app_name = 'setup'

urlpatterns = [
    path('', views.wizard_home, name='home'),
    path('institucion/', views.step_institucion, name='institucion'),
    path('materias/', views.step_materias, name='materias'),
    path('tipos-aporte/', views.step_tipos_aporte, name='tipos_aporte'),
    path('niveles/', views.step_niveles, name='niveles'),
    path('docentes/', views.step_docentes, name='docentes'),
    path('clases/', views.step_clases, name='clases'),
    path('estudiantes/', views.step_estudiantes, name='estudiantes'),
    path('matriculas/', views.step_matriculas, name='matriculas'),
    path('whatsapp/', views.step_whatsapp, name='whatsapp'),
    # Acciones inline
    path('materias/<int:pk>/eliminar/', views.delete_materia, name='delete_materia'),
    path('tipos-aporte/<int:pk>/eliminar/', views.delete_tipo_aporte, name='delete_tipo_aporte'),
    path('niveles/<int:pk>/eliminar/', views.delete_nivel, name='delete_nivel'),
    path('docentes/<int:pk>/eliminar/', views.delete_docente, name='delete_docente'),
    path('clases/<int:pk>/eliminar/', views.delete_clase, name='delete_clase'),
    path('estudiantes/<int:pk>/eliminar/', views.delete_estudiante, name='delete_estudiante'),
    path('matriculas/<int:pk>/eliminar/', views.delete_matricula, name='delete_matricula'),
]
