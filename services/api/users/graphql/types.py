import graphene
from graphene_django import DjangoObjectType
from users.models import Usuario

class UserType(DjangoObjectType):
    class Meta:
        model = Usuario
        fields = ("id", "nombre", "rol", "email", "phone", "cedula", "auth_user")
