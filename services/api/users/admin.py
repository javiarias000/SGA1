from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from .models import Profile, Usuario


# ─── Profile inline en User ───────────────────────────────────────────────────

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Opciones de contraseña'
    fk_name = 'user'


# ─── Django User (auth) ───────────────────────────────────────────────────────

admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'get_nombre_usuario', 'email', 'get_rol', 'is_staff', 'is_active')
    list_filter  = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_nombre_usuario(self, obj):
        try:
            return obj.usuario.nombre
        except Exception:
            return f'{obj.first_name} {obj.last_name}'.strip() or '—'
    get_nombre_usuario.short_description = 'Nombre'

    def get_rol(self, obj):
        ROL_COLORS = {
            'DOCENTE':     ('#1e40af', '#dbeafe'),
            'ESTUDIANTE':  ('#166534', '#dcfce7'),
            'PENDIENTE':   ('#854d0e', '#fef9c3'),
            'ADMIN':       ('#6d28d9', '#ede9fe'),
        }
        if obj.is_superuser or obj.is_staff:
            c, bg = ROL_COLORS['ADMIN']
            return format_html(
                '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;">ADMIN</span>',
                bg, c,
            )
        try:
            rol = obj.usuario.rol
            c, bg = ROL_COLORS.get(rol, ('#374151', '#f3f4f6'))
            return format_html(
                '<span style="background:{};color:{};padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
                bg, c, rol,
            )
        except Exception:
            return '—'
    get_rol.short_description = 'Rol'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# ─── Usuario (dominio central) ────────────────────────────────────────────────

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'get_rol_badge', 'email', 'cedula',
                     'phone', 'get_perfil_link', 'get_auth_user']
    list_filter   = ['rol']
    search_fields = ['nombre', 'email', 'cedula', 'auth_user__username']
    autocomplete_fields = ['auth_user']
    list_per_page = 30

    ROL_PALETTE = {
        'DOCENTE':    ('#1e40af', '#dbeafe'),
        'ESTUDIANTE': ('#166534', '#dcfce7'),
        'PENDIENTE':  ('#854d0e', '#fef9c3'),
    }

    fieldsets = (
        ('Identidad', {
            'fields': ('nombre', 'rol', 'cedula'),
        }),
        ('Contacto', {
            'fields': ('email', 'phone'),
        }),
        ('Acceso al sistema', {
            'fields': ('auth_user',),
        }),
    )

    def get_rol_badge(self, obj):
        c, bg = self.ROL_PALETTE.get(obj.rol, ('#374151', '#f3f4f6'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            bg, c, obj.rol,
        )
    get_rol_badge.short_description = 'Rol'
    get_rol_badge.admin_order_field = 'rol'

    def get_perfil_link(self, obj):
        """Link al perfil de Student o Teacher según el rol."""
        if obj.rol == 'ESTUDIANTE':
            try:
                sp = obj.student_profile
                url = reverse('admin:students_student_change', args=[sp.pk])
                return format_html('<a href="{}">👤 Ver estudiante</a>', url)
            except Exception:
                return format_html('<span style="color:#9CA3AF">Sin perfil estudiante</span>')
        if obj.rol == 'DOCENTE':
            try:
                tp = obj.teacher_profile
                url = reverse('admin:teachers_teacher_change', args=[tp.pk])
                return format_html('<a href="{}">👩‍🏫 Ver docente</a>', url)
            except Exception:
                return format_html('<span style="color:#9CA3AF">Sin perfil docente</span>')
        return '—'
    get_perfil_link.short_description = 'Perfil'

    def get_auth_user(self, obj):
        if not obj.auth_user:
            return format_html('<span style="color:#9CA3AF">Sin cuenta</span>')
        url = reverse('admin:auth_user_change', args=[obj.auth_user_id])
        return format_html('<a href="{}">🔑 {}</a>', url, obj.auth_user.username)
    get_auth_user.short_description = 'Cuenta'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('auth_user')
