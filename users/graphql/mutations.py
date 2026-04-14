import graphene
from users.models import Usuario
from .types import UserType

class CreateUserMutation(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        rol = graphene.String(required=True)
        email = graphene.String()
        phone = graphene.String()
        cedula = graphene.String()

    user = graphene.Field(UserType)

    def mutate(root, info, nombre, rol, email=None, phone=None, cedula=None):
        user = Usuario(
            nombre=nombre,
            rol=rol,
            email=email,
            phone=phone,
            cedula=cedula
        )
        user.save()
        return CreateUserMutation(user=user)

class UpdateUserMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        rol = graphene.String()
        email = graphene.String()
        phone = graphene.String()
        cedula = graphene.String()

    user = graphene.Field(UserType)

    def mutate(root, info, id, nombre=None, rol=None, email=None, phone=None, cedula=None):
        try:
            user = Usuario.objects.get(pk=id)
        except Usuario.DoesNotExist:
            return None

        if nombre is not None:
            user.nombre = nombre
        if rol is not None:
            user.rol = rol
        if email is not None:
            user.email = email
        if phone is not None:
            user.phone = phone
        if cedula is not None:
            user.cedula = cedula
        
        user.save()
        return UpdateUserMutation(user=user)

class DeleteUserMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(root, info, id):
        try:
            user = Usuario.objects.get(pk=id)
        except Usuario.DoesNotExist:
            return DeleteUserMutation(success=False)
        
        user.delete()
        return DeleteUserMutation(success=True)
