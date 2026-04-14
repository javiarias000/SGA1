from django.contrib import admin
from django.urls import path, include
from users.views.home import home_view
from django.conf import settings
from django.conf.urls.static import static
from graphene_django.views import GraphQLView
from music_registry.anonymous_graphql_view import AnonymousGraphQLView # Import custom view
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('admin/', admin.site.urls),
    
     # Vista principal (landing pública)
    path('', home_view, name='home'),
    
    # GraphQL Endpoint - Temporarily using AnonymousGraphQLView for migration
    path("graphql/", csrf_exempt(AnonymousGraphQLView.as_view(graphiql=True))), # Use AnonymousGraphQLView

    # API endpoints
    path('api/', include('users.api.urls')),

    # Autenticación y home (namespaced)
    path('users/', include(("users.urls", "users"), namespace='users')),

    # Apps principales (namespaced)
    path('students/', include(("students.urls", "students"), namespace='students')),
    path('teachers/', include(("teachers.urls", "teachers"), namespace='teachers')),
    path('classes/', include(("classes.urls", "classes"), namespace='classes')),
    path('academia/', include(("academia.urls", "academia"), namespace='academia')), # Include academia app URLs
    
] + (static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) if settings.DEBUG else [])
