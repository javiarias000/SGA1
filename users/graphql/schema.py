import graphene
from .mutations import CreateUserMutation, UpdateUserMutation, DeleteUserMutation
from .queries import Query

class UserMutations(graphene.ObjectType):
    create_user = CreateUserMutation.Field()
    update_user = UpdateUserMutation.Field()
    delete_user = DeleteUserMutation.Field()

schema = graphene.Schema(query=Query, mutation=UserMutations)
