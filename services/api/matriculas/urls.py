from django.urls import path
from . import views

app_name = 'matriculas'

urlpatterns = [
    # Pública — estudiantes
    path('nueva/', views.NuevaMatriculaView.as_view(), name='nueva'),
    path('confirmacion/<uuid:codigo>/', views.confirmacion_view, name='confirmacion'),
    path('seguimiento/', views.seguimiento_view, name='seguimiento'),
    path('renovacion/', views.renovacion_view, name='renovacion'),

    # Pública — docentes / personal
    path('registro-docente/', views.registro_docente_view, name='registro_docente'),
    path('registro-docente/confirmacion/<uuid:codigo>/',
         views.registro_docente_confirmacion_view, name='registro_docente_confirmacion'),

    # Secretaría
    path('secretaria/', views.secretaria_lista_view, name='secretaria_lista'),
    path('secretaria/<int:pk>/', views.secretaria_detalle_view, name='secretaria_detalle'),
    path('secretaria/<int:pk>/relanzar-ia/', views.secretaria_relanzar_ia_view, name='secretaria_relanzar_ia'),
]
