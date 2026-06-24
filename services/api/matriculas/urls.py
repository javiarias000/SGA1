from django.urls import path
from . import views

app_name = 'matriculas'

urlpatterns = [
    # Pública
    path('nueva/', views.NuevaMatriculaView.as_view(), name='nueva'),
    path('confirmacion/<uuid:codigo>/', views.confirmacion_view, name='confirmacion'),
    path('seguimiento/', views.seguimiento_view, name='seguimiento'),

    # Estudiante autenticado
    path('renovacion/', views.renovacion_view, name='renovacion'),

    # Secretaría
    path('secretaria/', views.secretaria_lista_view, name='secretaria_lista'),
    path('secretaria/<int:pk>/', views.secretaria_detalle_view, name='secretaria_detalle'),
    path('secretaria/<int:pk>/relanzar-ia/', views.secretaria_relanzar_ia_view, name='secretaria_relanzar_ia'),
]
