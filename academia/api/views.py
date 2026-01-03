from rest_framework import viewsets
from academia.models import Horario
from academia.serializers import HorarioSerializer

class HorarioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Horario.objects.all().select_related('curso', 'docente__usuario', 'clase') # Prefetch related data
    serializer_class = HorarioSerializer