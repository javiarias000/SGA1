import graphene
from users.models import Usuario
from .types import UserType

class Query(graphene.ObjectType):
    all_users = graphene.List(UserType)
    user_by_id = graphene.Field(UserType, id=graphene.Int(required=True))

    def resolve_all_users(root, info):
        return Usuario.objects.all()

    def resolve_user_by_id(root, info, id):
        try:
            return Usuario.objects.get(pk=id)
        except Usuario.DoesNotExist:
            return None
