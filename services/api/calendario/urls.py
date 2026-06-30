from django.urls import path
from . import views

app_name = 'calendario'

urlpatterns = [
    path('', views.calendario_view, name='calendario'),
    path('api/eventos/', views.eventos_json_view, name='eventos_json'),
    path('<int:pk>/eliminar/', views.eliminar_evento_view, name='eliminar_evento'),
]
