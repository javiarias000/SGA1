from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.lista_instrumentos_view, name='lista'),
    path('nuevo/', views.crear_instrumento_view, name='crear'),
    path('<int:pk>/', views.detalle_instrumento_view, name='detalle'),
    path('<int:pk>/prestamo/', views.prestamo_view, name='prestamo'),
    path('prestamo/<int:prestamo_id>/devolucion/', views.devolucion_view, name='devolucion'),
]
