from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# 1. Desregistrar el UserAdmin que viene por defecto
admin.site.unregister(User)

# 2. Definir un "inline" para el modelo Profile
# Esto permite ver y editar el perfil (ej. must_change_password)
# directamente desde la página de edición del Usuario.
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario'
    fk_name = 'user'

# 3. Crear un UserAdmin personalizado
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    
    # Columnas a mostrar en la lista de usuarios
    list_display = ('username', 'email', 'nombre_completo', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # 4. Método personalizado para mostrar el nombre completo correctamente
    @admin.display(description='Nombre Completo (Apellidos Nombres)')
    def nombre_completo(self, obj):
        """
        Combina los campos en el formato: Apellidos Nombres
        Ej: Arias Cuenca Jorge Javier
        """
        return f"{obj.last_name} {obj.first_name}"

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# Opcional: Registrar el modelo Profile por separado si también se quiere
# acceder a él directamente (además del inline).
# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'must_change_password')
#     list_filter = ('must_change_password',)
#     search_fields = ('user__username', 'user__email')
