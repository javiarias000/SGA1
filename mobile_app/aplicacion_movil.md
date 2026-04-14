# Plan de Desarrollo de Aplicación Móvil (Flutter) para SGA

Este documento detalla el plan para desarrollar una aplicación móvil utilizando Flutter, que interactuará con el backend de Django existente para el sistema SGA.

## 1. Configuración del Proyecto Flutter

### 1.1 Inicialización del Proyecto
- [X] Crear un nuevo proyecto Flutter utilizando `flutter create`. (Completado: Proyecto `mobile_app` creado)
- [X] Configurar la estructura de carpetas para módulos, servicios, modelos, etc. (Completado: `mobile_app/lib/api`, `mobile_app/lib/models`, `mobile_app/lib/services`, `mobile_app/lib/router`, `mobile_app/lib/providers`, `mobile_app/lib/screens` creados)

### 1.2 Dependencias Esenciales
- [X] `http` o `dio`: Para realizar peticiones HTTP a la API de Django. (Completado: `http` agregado a `pubspec.yaml` y `flutter pub get` ejecutado)
- [X] `provider`, `riverpod` o `bloc`: Para la gestión de estado de la aplicación. (Completado: `provider` agregado y configurado)
- [X] `shared_preferences` o `flutter_secure_storage`: Para el almacenamiento seguro de tokens de autenticación y preferencias de usuario. (Completado: `shared_preferences` agregado y usado en `AuthService`)
- [X] `go_router` o `fluro`: Para la gestión de rutas y navegación. (Completado: `go_router` agregado y configurado)
- [ ] `flutter_svg`: Si hay necesidad de usar imágenes SVG (común para íconos).

## 2. Integración con la API de Django

### 2.1 Definición de Endpoints
- [X] Revisar y documentar los endpoints REST API existentes en el backend de Django (`academia`, `students`, `teachers`, `subjects`, `users`). (Completado: `/api/token/auth/`, `/academia/api/v1/horarios/`, `/students/api/v1/students/`, `/teachers/api/v1/teachers/`, `/classes/api/v1/clases/` identificados y modelos relacionados analizados para obtener Subjects)
- [ ] Definir cualquier endpoint adicional que sea necesario para la funcionalidad móvil específica.

### 2.2 Modelos de Datos
- [X] Crear clases de modelo Dart (`.dart`) que reflejen las estructuras de datos JSON devueltas por la API de Django (serialización/deserialización). Utilizar `json_serializable` para facilitar este proceso.
    - [X] `Horario` model creado en `mobile_app/lib/models/horario.dart` (Refinado con anidamiento).
    - [X] `User` model creado en `mobile_app/lib/models/user.dart`.
    - [X] `GradeLevel` model creado en `mobile_app/lib/models/grade_level.dart`.
    - [X] `Subject` model creado en `mobile_app/lib/models/subject.dart`.
    - [X] `Student` model creado en `mobile_app/lib/models/student.dart`.
    - [X] `Teacher` model creado en `mobile_app/lib/models/teacher.dart`.
    - [X] `Clase` model creado en `mobile_app/lib/models/clase.dart`.

### 2.3 Servicios de API
- [X] Implementar una capa de servicios (`api_service.dart`) que encapsule todas las llamadas a la API de Django.
    - [X] `ApiService` creado en `mobile_app/lib/api/api_service.dart` con `fetchHorarios`, `fetchStudents`, `fetchTeachers`, `fetchClases`, `fetchStudentDetail`, `fetchTeacherDetail`, `fetchHorarioDetail` usando los modelos refinados y un método `login` que retorna el token.
    - [X] `ApiService` refactorizado para no gestionar el token internamente, recibiéndolo para peticiones autenticadas.
- [ ] Métodos para:
    - CRUD para `subjects`, `academia`.
    - Manejo de errores específicos de la API.

## 3. Autenticación y Autorización

### 3.1 Flujo de Autenticación
- [X] Implementar pantallas de registro y login. (Completado: `LoginScreen` básica implementada y ruta configurada con `go_router`. Lógica de login manejada por `AuthProvider`.)
- [X] Enviar credenciales al backend de Django y recibir tokens de autenticación (JWT o Token simple). (Lógica implementada en `ApiService` y `AuthService`)

### 3.2 Gestión de Tokens
- [X] Almacenar de forma segura los tokens (acceso y refresco) en el dispositivo. (Completado: `AuthService` usa `shared_preferences` para almacenar y recuperar el token)
- [X] Implementar la lógica para adjuntar el token de acceso en todas las peticiones a la API. (Implementado en `ApiService` para todos los métodos de `fetch` a través de `AuthService`)
- [X] Manejo de sesiones expiradas y redirección al login. (Completado: `go_router` redirige al login si no hay sesión al iniciar. Adicionalmente, si el token expira durante una sesión, un error 401 en la API es capturado, provocando el cierre de sesión y la redirección al login de forma automática.)

## 4. Desarrollo de la Interfaz de Usuario (UI/UX)

### 4.1 Arquitectura UI
- [X] Dividir la UI en widgets reutilizables y pantallas lógicas. (Completado: `main.dart` ahora usa `LoginScreen`, `MyHomePage`, `StudentsListScreen`, `TeachersListScreen`, `SubjectsListScreen`, `StudentDetailScreen`, `TeacherDetailScreen`, `HorarioDetailScreen` y la navegación es manejada por `go_router`. Clases y servicios separados por archivos.)
- [ ] Implementar un diseño consistente siguiendo los principios de Material Design o Cupertino (para iOS).

### 4.2 Módulos Principales (Basados en las apps de Django)

#### 4.2.1 Pantalla de Inicio/Dashboard
- [X] Vista general o navegación principal a las secciones de la aplicación. (Completado: `MyHomePage` actúa como un dashboard básico después del login, mostrando horarios y enlaces a estudiantes, docentes y materias)

#### 4.2.2 Módulo de Academia
- [X] Listado de cursos, asignaturas y horarios. (Completado: Listado de `Horario` en `MyHomePage` con objetos anidados, utilizando `HorarioProvider`. Tappable para ver detalle.)
- [X] Detalles de cada curso/asignatura. (Completado: `HorarioDetailScreen` implementado.)

#### 4.2.3 Módulo de Estudiantes
- [X] Listado de estudiantes con opción de búsqueda/filtrado. (Completado: `StudentsListScreen` con `StudentProvider` para listar estudiantes. Tappable para ver detalle.)
- [X] Pantalla de perfil de estudiante (información personal, historial académico, asignaciones). (Completado: `StudentDetailScreen` implementado.)

#### 4.2.4 Módulo de Docentes
- [X] Listado de docentes con opción de búsqueda/filtrado. (Completado: `TeachersListScreen` con `TeacherProvider` para listar docentes. Tappable para ver detalle.)
- [X] Pantalla de perfil de docente (información de contacto, asignaturas impartidas, horarios). (Completado: `TeacherDetailScreen` implementado.)

#### 4.2.5 Módulo de Asignaturas
- [X] Listado de todas las asignaturas disponibles. (Completado: `SubjectsListScreen` con `SubjectProvider` para listar materias, derivado de `ClaseProvider`.)
- [X] Detalles de cada asignatura (descripción, docentes, estudiantes matriculados). (Completado: `SubjectDetailScreen` implementado. Muestra los detalles de la asignatura y una lista de los docentes que la imparten, obteniendo los datos al filtrar la lista de Clases.)

### 4.3 Navegación
- [X] Implementar la navegación entre las diferentes pantallas utilizando `go_router` o similar. (Completado: `go_router` configurado para `login`, `home`, `students`, `student_detail`, `teachers`, `teacher_detail`, `horario_detail` y `subjects`, utilizando `AuthProvider` para redirecciones.)

## 5. Gestión de Estado

- [X] Implementar la solución de gestión de estado elegida (Provider, Riverpod, Bloc) para manejar el flujo de datos y la reactividad de la UI. (Completado: `Provider` implementado con `AuthProvider`, `HorarioProvider`, `StudentProvider`, `TeacherProvider`, `ClaseProvider`, `SubjectProvider`.)

## 6. Manejo de Errores y Feedback al Usuario

- [X] Mostrar mensajes de error claros y amigables. (Completado: En `LoginScreen`, `MyHomePage`, `StudentsListScreen`, `TeachersListScreen`, `SubjectsListScreen`, `StudentDetailScreen`, `TeacherDetailScreen`, `HorarioDetailScreen`)
- [X] Implementar indicadores de carga (spinners) para operaciones asíncronas. (Completado: En `LoginScreen`, `MyHomePage`, `StudentsListScreen`, `TeachersListScreen`, `SubjectsListScreen`, `StudentDetailScreen`, `TeacherDetailScreen`, `HorarioDetailScreen`)
- [X] Notificaciones (toasts, snackbars) para acciones exitosas o advertencias. (Completado: Se han añadido notificaciones `SnackBar` para el inicio y cierre de sesión, mejorando el feedback al usuario.)

## 7. Pruebas

- [ ] **Unit Tests**: Para la lógica de negocio, servicios de API y modelos. (Pendiente: La configuración de mocks para las dependencias está en proceso.)
- [ ] **Widget Tests**: Para verificar el comportamiento de los widgets individuales.
- [ ] **Integration Tests**: Para probar flujos de usuario completos.

## 8. Despliegue (Alto Nivel)

- [ ] Generar builds para Android (APK/App Bundle) e iOS (IPA).
- [ ] Publicar en Google Play Store y Apple App Store.

---
**Consideraciones Adicionales:**
- **Internacionalización (i18n)**: Si la aplicación necesita soportar múltiples idiomas.
- **Notificaciones Push**: Integrar Firebase Cloud Messaging (FCM) si se requieren notificaciones.
- **Offline Capabilities**: Si es necesario que la aplicación funcione sin conexión a internet o con funcionalidades limitadas.

---
**Instrucciones para Probar la Conectividad de la API y la Autenticación:**

Para verificar la conectividad de la aplicación Flutter con el backend de Django, la autenticación y la carga de datos:

1.  **Asegúrate de que los servicios de Docker estén funcionando:**
    ```bash
    docker-compose up -d
    ```
    (Ya has ejecutado esto y verificado que están corriendo).

2.  **Ejecuta la aplicación Flutter:**
    Desde la terminal de tu máquina local (fuera de los contenedores Docker), navega al directorio `mobile_app` y ejecuta la aplicación en un emulador o dispositivo físico:
    ```bash
    cd mobile_app
    flutter run
    ```
    Si es la primera vez que ejecutas después de estas actualizaciones, el compilador puede pedirte que confirmes algunas cosas o que realices un `flutter clean` y luego `flutter run` de nuevo.

3.  **Proceso de Verificación:**
    *   La aplicación debería iniciar mostrando la **Login Screen**.
    *   Ingresa credenciales válidas para un usuario existente en tu sistema Django. (Por ejemplo, si tienes un superusuario, puedes usar esas credenciales).
    *   Si el login es exitoso, serás redirigido a la `MyHomePage` (la pantalla de horarios).
    *   En la `MyHomePage`, deberías ver una lista de "Horarios", y botones para "View Students", "View Teachers", y "View Subjects".
    *   Al hacer clic en un horario en la lista, serás navegado a la `HorarioDetailScreen` mostrando sus detalles.
    *   Al hacer clic en "View Students", serás navegado a la `StudentsListScreen`, donde debería aparecer una lista de estudiantes.
    *   Al hacer clic en un estudiante en la lista, serás navegado a la `StudentDetailScreen` mostrando sus detalles.
    *   Al hacer clic en "View Teachers", serás navegado a la `TeachersListScreen`, donde debería aparecer una lista de docentes.
    *   Al hacer clic en un docente en la lista, serás navegado a la `TeacherDetailScreen` mostrando sus detalles.
    *   Al hacer clic en "View Subjects", serás navegado a la `SubjectsListScreen`, donde debería aparecer una lista de materias.
    *   Si hay un problema de conexión o credenciales, verás un mensaje de error en la pantalla de login o en las pantallas de datos.

**Nota Importante:** Si estás ejecutando la aplicación Flutter en tu máquina local (no dentro del contenedor `flutter_dev`), y tu backend de Django está corriendo dentro de Docker, asegúrate de que tu máquina local pueda acceder al servicio `web` de Docker. Por lo general, si accedes a Django desde tu navegador en `localhost:8000`, la aplicación Flutter también debería poder hacerlo. Si tienes problemas de conexión, podrías necesitar configurar el puerto de Django para que sea accesible externamente o usar la IP del host de Docker si estás en un entorno de máquina virtual. En el código, `http://web:8000` funciona dentro de la red Docker; fuera de ella, podrías necesitar `http://localhost:8000` si Docker ha mapeado el puerto correctamente.