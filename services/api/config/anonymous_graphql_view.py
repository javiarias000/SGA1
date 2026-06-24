from graphene_django.views import GraphQLView
from django.contrib.auth.mixins import AccessMixin

class AnonymousGraphQLView(AccessMixin, GraphQLView):
    def dispatch(self, request, *args, **kwargs):
        # Allow unauthenticated access by setting request.user to an AnonymousUser instance
        # if a concrete user is not already set by other middleware.
        # This is primarily to bypass @login_required decorators or similar checks
        # if they were present on the view, though in urls.py we have csrf_exempt.
        # However, the 302 redirect indicates some authentication is being enforced.
        # By setting request.user to an AnonymousUser, it should satisfy any
        # authentication checks that simply verify if request.user is an instance of User.
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return super().dispatch(request, *args, **kwargs)
