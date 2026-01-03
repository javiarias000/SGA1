from django.urls import path, include

app_name = 'academia'

urlpatterns = [
    # API DRF
    path('api/v1/', include('academia.api.urls')),
]