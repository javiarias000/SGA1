# Documentación de Desarrollo de Aplicación Móvil (Flutter) - SGA

## Estado Actual del Desarrollo
La aplicación móvil ha sido desarrollada como un prototipo funcional completo que interactúa con el backend de Django.

### 1. Arquitectura y Stack Técnico
- **Framework:** Flutter (SDK ^3.10.7)
- **Gestión de Estado:** `provider`
- **Navegación:** `go_router` (con guardias de ruta basadas en roles)
- **Comunicación:** `http` (REST API)
- **Persistencia:** `shared_preferences` (Token de autenticación)

### 2. Funcionalidades Implementadas

#### Autenticación y Seguridad
- Flujo completo de Login y Logout.
- Almacenamiento seguro de tokens JWT.
- Gestión de sesiones expiradas (401 Unauthorized $\rightarrow$ Logout $\rightarrow$ Redirect Login).
- **Control de Acceso Basado en Roles (RBAC):**
    - `DOCENTE`/`ADMIN`: Acceso total a gestión de estudiantes, docentes y materias.
    - `ESTUDIANTE`: Acceso restringido a dashboard de horarios y sus propios datos.

#### Módulos de Gestión (Admin CRUD)
- **Estudiantes:** Listado, Detalle, Creación, Edición y Eliminación.
- **Docentes:** Listado, Detalle, Creación, Edición y Eliminación.
- **Asignaturas:** Listado, Detalle, Creación, Edición y Eliminación.

#### Operaciones Académicas
- **Matriculación (Enrollment):** Capacidad de inscribir estudiantes en clases específicas desde la vista de detalle del estudiante.
- **Sistema de Calificaciones:** Interfaz para que docentes ingresen notas por parcial y tipo de aporte, con visualización de historial.
- **Control de Asistencia:** Registro de asistencia diaria (Presente/Ausente/Justificado) y consulta de historial.

#### Dashboard y Navegación
- Vista de horarios optimizada con detalles de curso, aula y docente.
- Navegación centralizada mediante `AppRouter`.

### 3. Guía de Ejecución

#### Requisitos
- Flutter SDK instalado.
- Backend Django corriendo en Docker (`docker compose up -d`).

#### Pasos para ejecutar:
1. Navegar al directorio: `cd mobile_app`
2. Ejecutar dependencias: `flutter pub get`
3. Iniciar aplicación: `flutter run`

### 4. Mapa de Rutas (`go_router`)
- `/login`: Pantalla de acceso.
- `/`: Dashboard de horarios (Home).
- `/students`: Listado de estudiantes (Admin).
- `/students/:id`: Detalle de estudiante.
- `/teachers`: Listado de docentes (Admin).
- `/teachers/:id`: Detalle de docente.
- `/subjects`: Listado de materias (Admin).
- `/subjects/:id`: Detalle de materia.
- `/horarios/:id`: Detalle de horario.
