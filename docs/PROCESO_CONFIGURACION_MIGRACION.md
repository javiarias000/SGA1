# Documentación del Proceso de Configuración y Migración del Sistema

Este documento detalla los pasos realizados para solucionar problemas de autenticación, integrar GraphQL con la aplicación de usuarios y migrar usuarios (docentes y estudiantes) a la base de datos de manera que puedan iniciar sesión en el sistema.

---

## 1. Contexto Inicial y Problemas Identificados

### 1.1. Error 404 en `/login`

**Problema:** El sistema arrojaba un error 404 al intentar acceder a la URL `http://localhost:8000/login`.
**Análisis:** Se confirmó que la URL `/login` no estaba definida en el `ROOT_URLCONF`. La URL correcta, según la configuración de `users/urls.py`, es `/users/login/`. Sin embargo, para que Django redirija correctamente a esta URL en situaciones como el `@login_required` o el acceso al panel de administración, la configuración `LOGIN_URL` en `settings.py` debe estar explícitamente definida.
**Solución:** Se modificó `music_registry/settings.py` para descomentar y establecer `LOGIN_URL = '/users/login/'`.

### 1.2. Bucle de Redirección después de Login

**Problema:** Al hacer clic en el enlace "Login Sistema Académico" desde la página principal, un usuario ya autenticado entraba en un bucle de redirección (`/users/login/` -> `/teachers/dashboard/` -> `/`), terminando de vuelta en la página principal.
**Análisis:** Este comportamiento se debe a que la página de inicio mostraba un enlace de "Login" a usuarios que ya habían iniciado sesión. Al hacer clic, el sistema detectaba la autenticación y redirigía al usuario a su dashboard. Desde el dashboard, al no cumplir quizás con ciertos permisos o roles específicos para esa vista, se redirigía de nuevo a la página principal.
**Solución:** Se modificó `templates/home.html` para implementar una lógica condicional utilizando `{% if user.is_authenticated %}` y `{% else %}`.
    *   Si el usuario está autenticado: Se muestran enlaces para "Ir al Panel" (`users:dashboard`) y "Cerrar Sesión" (`users:logout`).
    *   Si el usuario no está autenticado: Se muestra el enlace original de "Login Sistema Académico" (`users:login`).
Esto garantiza una experiencia de usuario coherente y evita redirecciones innecesarias.

---

## 2. Autenticación del Backend

**Preguntas iniciales:**
1.  ¿El backend de Django está configurado para usar JWT (JSON Web Tokens) con tokens de refresco, o es `TokenAuthentication` simple?
2.  Si utiliza tokens de refresco, ¿el endpoint de login (`/api/token/auth/` o uno diferente) devuelve tanto el token de acceso como un token de refresco?
3.  ¿Hay un endpoint específico en el backend de Django para refrescar el token de acceso utilizando el token de refresco (por ejemplo, `/api/token/refresh/`)?

**Respuestas:**
1.  El backend está configurado para usar `TokenAuthentication` simple de Django Rest Framework. Se confirmó la presencia de `djangorestframework` en `requirements.txt` y la configuración `'rest_framework.authentication.TokenAuthentication'` en `music_registry/settings.py`. No se identificó ninguna librería JWT (ej. `djangorestframework-simplejwt`).
2.  El endpoint de login (`/api/token/auth/`) utiliza la vista `obtain_auth_token` de DRF, que solo devuelve un token de acceso (`token`). **No devuelve un token de refresco.**
3.  No existe un endpoint específico para refrescar tokens, ya que el sistema utiliza `TokenAuthentication` simple, que no incorpora el concepto de tokens de refresco.

---

## 3. Integración de Usuarios con GraphQL

Se extendió la funcionalidad de GraphQL para incluir el modelo `Usuario`, permitiendo consultas y mutaciones.

### 3.1. Definición de Tipos (Types)

*   **`users/graphql/types.py`**: Se creó este archivo para definir el `UserType` a partir del modelo `Usuario`.
    ```python
    import graphene
    from graphene_django import DjangoObjectType
    from users.models import Usuario

    class UserType(DjangoObjectType):
        class Meta:
            model = Usuario
            fields = ("id", "nombre", "rol", "email", "phone", "cedula", "auth_user")
    ```

### 3.2. Implementación de Consultas (Queries)

*   **`users/graphql/queries.py`**: Se creó este archivo para definir las consultas relacionadas con `Usuario`.
    ```python
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
    ```

### 3.3. Implementación de Mutaciones (Mutations)

*   **`users/graphql/mutations.py`**: Se creó este archivo para definir las mutaciones de `Usuario` (creación, actualización y eliminación).
    ```python
    import graphene
    from users.models import Usuario
    from .types import UserType

    class CreateUserMutation(graphene.Mutation):
        # ... argumentos y lógica para crear Usuario ...

    class UpdateUserMutation(graphene.Mutation):
        # ... argumentos y lógica para actualizar Usuario ...

    class DeleteUserMutation(graphene.Mutation):
        # ... argumentos y lógica para eliminar Usuario ...
    ```

### 3.4. Integración al Esquema Principal de GraphQL

*   **`users/graphql/schema.py`**: Se creó este archivo para agrupar las mutaciones específicas de `users`.
    ```python
    import graphene
    from .mutations import CreateUserMutation, UpdateUserMutation, DeleteUserMutation
    from .queries import Query # Se importó la Query para modularizar, aunque luego se heredó directamente en music_registry/schema.py

    class UserMutations(graphene.ObjectType):
        create_user = CreateUserMutation.Field()
        update_user = UpdateUserMutation.Field()
        delete_user = DeleteUserMutation.Field()

    schema = graphene.Schema(query=Query, mutation=UserMutations) # Este esquema local no es el que se usa directamente
    ```
*   **`music_registry/schema.py`**: Se modificó este archivo para incorporar las `Query` y `Mutation` definidas en `users/graphql/`.
    *   La clase `Query` principal ahora hereda de `users.graphql.queries.Query`.
    *   La clase `Mutation` principal ahora hereda de `users.graphql.schema.UserMutations`.
    *   Se eliminaron las definiciones redundantes de `UsuarioType` y sus `resolve_` métodos directamente del `music_registry/schema.py` para evitar duplicidad y mejorar la modularidad.

---

## 4. Migración de Usuarios para Iniciar Sesión

El objetivo fue habilitar la funcionalidad de inicio de sesión para los `Usuario`s (docentes y estudiantes) existentes en la base de datos, asegurando que cada `Usuario` tenga un `auth_user` asociado.

### 4.1. Modificación de `teachers/management/commands/import_teachers.py`

**Propósito:** Este script se actualizó para no solo crear o actualizar el perfil `Usuario` y `Teacher`, sino también para crear o vincular un `auth_user` de Django, permitiendo el inicio de sesión.

**Lógica Implementada:**
*   Se importó el modelo `User` de `django.contrib.auth.models`.
*   Para cada `entry` de docente en el JSON:
    *   Se obtiene o crea el objeto `Usuario` (`Usuario.objects.get_or_create`).
    *   **Manejo del `auth_user`**:
        *   Si `usuario.auth_user` es `None` (no hay usuario de autenticación vinculado):
            *   Se genera un `username` a partir del email o `username` del JSON.
            *   **Se asegura la unicidad del `username`**: Si el `username` ya existe en el modelo `User`, se le añade un sufijo numérico (`_1`, `_2`, etc.) hasta que sea único.
            *   Se crea un **nuevo** `User` con este `username` único.
            *   Se establece la contraseña (`set_password`) usando `password_plano` del JSON, o una contraseña inutilizable si no se provee.
            *   Se actualizan `email`, `first_name` y `last_name` del `auth_user`.
            *   Se vincula el `auth_user` al `usuario` (`usuario.auth_user = auth_user`).
        *   Si `usuario.auth_user` ya existe:
            *   Se actualiza la contraseña y el email del `auth_user` si la información del JSON es diferente.
            *   Se actualizan `first_name` y `last_name` si están disponibles.
*   Se registraron contadores para `auth_user` creados y vinculados.

### 4.2. Modificación de `students/management/commands/import_students.py`

**Propósito:** Similar al script de docentes, este se actualizó para crear o vincular un `auth_user` para cada `Usuario` estudiante.

**Lógica Implementada:**
*   Se importó el modelo `User` de `django.contrib.auth.models`.
*   Para cada `entry` de estudiante en el JSON:
    *   **Lógica robusta de obtención/creación de `Usuario`**:
        *   Se prioriza la búsqueda de `Usuario` por `cedula` (campo `unique=True`).
        *   Si no se encuentra por `cedula`, se busca por `email` (también `unique=True`).
        *   Si se encuentra, se actualizan los campos del `Usuario` existente. Se añadió una verificación para el `email` antes de actualizar para evitar `IntegrityError` por duplicados.
        *   Si no se encuentra, se crea un nuevo `Usuario` con los datos disponibles, manejando `IntegrityError` si el email estuviera duplicado.
    *   **Manejo del `auth_user` (similar al de docentes)**:
        *   Si `usuario.auth_user` es `None`:
            *   Se deriva un `username` a partir del email o `cedula` del estudiante.
            *   **Se asegura la unicidad del `username`**: Se genera un `username` único.
            *   Se crea un **nuevo** `User` con este `username` único.
            *   Se establece una **contraseña por defecto "temporal123"** (ya que el JSON de estudiantes no contiene `password_plano`).
            *   Se actualizan `email`, `first_name` y `last_name` del `auth_user`.
            *   Se vincula el `auth_user` al `usuario`.
        *   Si `usuario.auth_user` ya existe:
            *   Se establece la contraseña por defecto "temporal123" si no está establecida o es diferente.
            *   Se actualiza el `email` del `auth_user` si ha cambiado y no causa un conflicto de unicidad con otro `Usuario`.
            *   Se actualizan `first_name` y `last_name`.
*   Se registraron contadores para `auth_user` creados y vinculados.

### 4.3. Manejo de Señales en `users/signals.py`

**Problema:** La señal `create_or_update_usuario_profile` en `users/signals.py` se activaba cada vez que se guardaba un `User`, intentando crear o vincular automáticamente un `Usuario`. Esto generaba conflictos y `IntegrityError` (ej., `duplicate key value violates unique constraint "users_usuario_email_key"`), ya que los scripts de importación ya manejaban la creación y vinculación de `Usuario`s.

**Solución:** Se comentó temporalmente el `receiver` de la señal `create_or_update_usuario_profile` en `users/signals.py` antes de ejecutar los comandos de importación.

**Pasos:**
1.  **Comentar** la señal en `users/signals.py`.
2.  **Ejecutar** los comandos de importación:
    *   `docker compose exec web python manage.py import_teachers`
    *   `docker compose exec web python manage.py import_students`
3.  **Descomentar** la señal en `users/signals.py` para restaurar el comportamiento normal de la aplicación.

### 4.4. Comandos de Migración Ejecutados (Docker)

Los comandos para ejecutar los scripts de importación dentro del entorno Docker son:

1.  **Para Profesores:**
    ```bash
    docker compose exec web python manage.py import_teachers
    ```
    *   Resultado: 40 `auth_user`s creados y vinculados con éxito, actualizando los `Usuario`s y `Teacher`s existentes.

2.  **Para Estudiantes:**
    ```bash
    docker compose exec web python manage.py import_students
    ```
    *   Resultado: Numerosos `auth_user`s creados y vinculados con éxito para los estudiantes, actualizando los `Usuario`s y `Student`s existentes. Las advertencias de "Skipping email update..." confirman que la lógica de unicidad de email funcionó correctamente.

---

## 5. Consideraciones Importantes y Lecciones Aprendidas

*   **Robustez de `get_or_create`**: Es crucial usar identificadores verdaderamente únicos (`cedula`, `email`) en las condiciones de `get_or_create` para evitar errores `MultipleObjectsReturned` o `IntegrityError`. El fallback a campos no únicos como el `nombre` puede ser problemático.
*   **Manejo de `OneToOneField`**: Al vincular modelos (`Usuario` con `User` a través de `auth_user`), es vital asegurarse de que el `auth_user` no esté ya vinculado a otro objeto `Usuario`, o generar uno nuevo si es necesario para evitar conflictos de unicidad.
*   **Impacto de las Señales de Django**: Las señales `post_save` pueden ser muy útiles, pero pueden causar conflictos inesperados durante operaciones de importación masiva o cuando la lógica de los scripts ya maneja la creación/actualización de objetos relacionados. Deshabilitarlas temporalmente puede ser una estrategia necesaria.
*   **Unicidad del Email/Username**: En sistemas de autenticación, el email y el username deben ser únicos. Si los datos de origen tienen duplicados, es necesario implementar una lógica de desduplicación (ej., añadiendo sufijos) o de manejo de conflictos (ej., no actualizar el email si ya está en uso).
*   **Contraseñas por Defecto**: Para usuarios importados sin contraseña, es una buena práctica establecer una contraseña por defecto (ej., "temporal123") y forzar un cambio en el primer inicio de sesión.
*   **Modularización GraphQL**: Mantener los tipos, queries y mutations de cada aplicación en sus propios archivos `graphql/types.py`, `graphql/queries.py`, `graphql/mutations.py` y `graphql/schema.py` mejora significativamente la organización y mantenibilidad del esquema GraphQL principal.
*   **Configuración `LOGIN_URL`**: Definir explícitamente `LOGIN_URL` en `settings.py` es fundamental para el correcto funcionamiento de las redirecciones de autenticación de Django.
*   **Experiencia de Usuario en Plantillas**: Condicionar la visibilidad de enlaces (Login/Logout/Dashboard) según el estado de autenticación del usuario mejora la usabilidad y evita confusiones.
