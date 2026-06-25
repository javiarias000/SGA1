# SGA1 — Sistema de Gestión Académica

Sistema integral de gestión académica para el **Conservatorio Bolívar de Ambato**. Monorepo con arquitectura de microservicios que centraliza estudiantes, docentes, calificaciones, asistencia, matrículas y notificaciones por WhatsApp.

**URL de producción:** `https://sga1.12t4ag.easypanel.host`

---

## Índice

1. [Servicios](#servicios)
2. [Estructura del Repositorio](#estructura-del-repositorio)
3. [Inicio Rápido](#inicio-rápido)
4. [Panel de Administración](#panel-de-administración)
5. [Wizard de Configuración](#wizard-de-configuración)
6. [Importación Masiva desde Google Sheets](#importación-masiva-desde-google-sheets)
7. [Dashboard del Docente](#dashboard-del-docente)
8. [Admin Django organizado por jerarquía](#admin-django-organizado-por-jerarquía)
9. [Comandos Makefile](#comandos-makefile)
10. [ETL — Importar datos del conservatorio](#etl--importar-datos-del-conservatorio)
11. [API REST — Módulo informes](#api-rest--módulo-informes)
12. [Servicio WhatsApp (Node.js)](#servicio-whatsapp-nodejs)
13. [Variables de Entorno](#variables-de-entorno)
14. [Modelo de Datos Principal](#modelo-de-datos-principal)
15. [Grupos de Niveles (Conservatorio)](#grupos-de-niveles-conservatorio)
16. [Desarrollo Local](#desarrollo-local)

---

## Servicios

| Servicio | Tecnología | Puerto interno | Descripción |
|----------|-----------|----------------|-------------|
| `api` | Django 5.2 + DRF + GraphQL | 8000 | API principal: dominio académico + informes WhatsApp |
| `whatsapp` | Node.js + Express | 3001 | Google Sheets, proxy `/api/informes/*` → Django |
| `mobile` | Flutter Web + nginx | 80 | App móvil web |
| `django_web` | nginx → Django | 8001 | Panel web (admin, templates) |
| `db` | PostgreSQL 15 | 5432 | Base de datos principal |
| `redis` | Redis 7 | 6379 | Broker Celery |

> **Conflictos de puertos conocidos en este servidor:**
> - Puerto 8000 → ocupado por `Appointment-Booking-Automator` (no matar)
> - Puerto 5432 → ocupado por `elated_hamilton` (no matar)
> - Solución activa: `API_HOST_PORT=8002`, `DB_PORT=5434` en `.env`

---

## Estructura del Repositorio

```
SGA1/
├── services/
│   ├── api/                    ← Django backend (fuente de verdad)
│   │   ├── config/             ← Settings, URLs, Celery, WSGI
│   │   ├── users/              ← Usuario central, auth backend, GraphQL
│   │   ├── students/           ← Perfil de estudiante (extiende Usuario)
│   │   ├── teachers/           ← Perfil de docente (extiende Usuario)
│   │   ├── subjects/           ← Materias (INSTRUMENTO / TEORIA / AGRUPACION)
│   │   ├── classes/            ← GradeLevel, Clase, Enrollment, Calificaciones, Asistencia
│   │   ├── setup/              ← Wizard de configuración institucional (9 pasos)
│   │   ├── docente/            ← Panel dashboard del docente
│   │   ├── academia/           ← REST API views y serializers
│   │   ├── agente/             ← Agente IA académico
│   │   ├── informes/           ← Informes WhatsApp, Evolution API
│   │   ├── matriculas/         ← Gestión de matrículas en línea
│   │   └── templates/          ← Templates globales (admin, home, emails)
│   ├── whatsapp/               ← Servicio Node.js
│   │   ├── public/             ← Frontend WhatsApp (index.html, calificaciones.html)
│   │   ├── server.js           ← Express: Google Sheets + proxy a Django
│   │   └── Dockerfile
│   └── mobile/                 ← App Flutter
├── infra/
│   ├── Dockerfile.api          ← Imagen Django
│   ├── nginx/                  ← nginx.conf, nginx_django.conf
│   └── scripts/                ← init-db.sh, wait-for-db.sh
├── data/
│   ├── archivos_formularios/   ← Scripts ETL y archivos raw
│   ├── base_de_datos_json/     ← JSON fuente (matrícula, estudiantes, docentes)
│   └── backups/                ← Backups PostgreSQL
├── docs/                       ← Documentación extendida
├── docker-compose.yml
├── docker-compose.override.yml ← Overrides de desarrollo
├── Makefile
└── .env
```

---

## Inicio Rápido

### Prerrequisitos

- Docker + Docker Compose
- Git

### 1. Clonar y configurar

```bash
git clone https://github.com/javiarias000/SGA1.git
cd SGA1
cp .env.backend.example .env
# Editar .env con tus credenciales
```

### 2. Levantar todos los servicios

```bash
make up
# o directamente:
docker compose up -d
```

### 3. Crear usuario administrador

```bash
docker exec sga1_api python manage.py createsuperuser
```

> Credenciales actuales de desarrollo: `admin` / `Admin1234!`

### 4. Acceder al sistema

| URL | Qué es |
|-----|--------|
| `https://sga1.12t4ag.easypanel.host/` | Inicio del sitio |
| `https://sga1.12t4ag.easypanel.host/admin/` | Panel Django Admin |
| `https://sga1.12t4ag.easypanel.host/setup/` | Wizard de Configuración |
| `https://sga1.12t4ag.easypanel.host/docente/` | Dashboard del Docente |
| `https://sga1.12t4ag.easypanel.host/users/login/` | Login |

---

## Panel de Administración

El panel admin Django está en `/admin/` y organiza todos los módulos por **jerarquía de datos** (ver sección [Admin Django](#admin-django-organizado-por-jerarquía)).

Desde la barra superior del admin hay acceso directo al **⚙️ Wizard de Configuración**.

---

## Wizard de Configuración

El wizard en `/setup/` guía al administrador por **9 pasos ordenados** para configurar la institución desde cero:

| Paso | Sección | Qué se configura |
|------|---------|-----------------|
| 1 | Institución | Nombre, siglas, ciudad, año lectivo, misión y visión |
| 2 | Materias | Asignaturas: Instrumento, Teoría, Agrupación |
| 3 | Tipos de Aporte | Criterios de calificación: Trabajo en clase, Exposición, Transcripción, etc. |
| 4 | Niveles / Cursos | Años y paralelos (Básica 1 A, Media 3 B, Superior 7 C…) |
| 5 | Docentes | Registro de profesores con usuario de acceso auto-creado |
| 6 | Clases | Asignación: materia + docente + nivel/paralelo |
| 7 | Estudiantes | Registro de alumnos con datos del representante (WhatsApp) |
| 8 | Matrículas | Inscripción de estudiantes en clases |
| 9 | WhatsApp | Configurar instancia Evolution API para notificaciones |

### Características UX del wizard

- Sidebar izquierdo oscuro con **indicador de progreso** (✅ completado / 🔵 activo / ⬡ pendiente)
- Barra de progreso porcentual en tiempo real
- Cada paso muestra la lista existente + formulario de alta en la misma pantalla
- Botones Anterior / Continuar en todos los pasos
- Accesible solo para staff (`is_staff=True`)

### Selector de Niveles agrupado

El selector de nivel/paralelo en los pasos Clases y Estudiantes muestra los niveles **agrupados jerárquicamente**:

```
Básica  —  1° y 2°
  ├── Básica 1 'A'
  └── Básica 2 'A'

Media  —  3° al 5°
  ├── Media 3 'A'
  ├── Media 4 'B'
  └── Media 5 'A'

Superior  —  6° al 11°
  ├── Superior 6 'A'
  ├── Superior 7 'A'
  └── ...
```

---

## Flujo de Auto-Registro (Links Públicos)

En `/setup/links/` el administrador encuentra los **tres links compartibles** del sistema:

### Links disponibles

| Link | Público | Cuándo compartir |
|------|---------|-----------------|
| `/matriculas/registro-docente/` | ✅ Sin login | Una sola vez al instalar, o cuando llega un docente nuevo |
| `/matriculas/nueva/` | ✅ Sin login | Inicio de cada año lectivo (nuevos estudiantes) |
| `/matriculas/renovacion/` | Login del estudiante | Inicio de cada año lectivo (renovación anual) |

### Flujo completo

```
DOCENTE NUEVO
  → Recibe link /matriculas/registro-docente/
  → Llena: nombre, cédula, email, teléfono, especialidad, título, experiencia
  → Admin recibe solicitud en Admin → Matrículas → Solicitudes Registro Docentes
  → Admin hace clic en "✅ Aprobar y crear cuenta de docente"
  → Sistema crea automáticamente: auth.User + Usuario(DOCENTE) + Teacher
  → Credenciales enviadas por WhatsApp al teléfono del docente

ESTUDIANTE NUEVO (cada año)
  → Representante recibe link /matriculas/nueva/
  → Llena: datos del alumno + datos del representante + documentos (cédula, certificados, foto)
  → Secretaría revisa en /matriculas/secretaria/ o Admin Django
  → Secretaría aprueba → Sistema crea: auth.User + Usuario(ESTUDIANTE) + Student
  → Credenciales enviadas al WhatsApp del representante

ESTUDIANTE EXISTENTE (renovación anual)
  → Recibe mensaje con link /matriculas/renovacion/
  → Inicia sesión con su cuenta
  → Sube documentos de renovación (el sistema detecta automáticamente el año siguiente)
  → Secretaría aprueba → matrículas actualizadas para el nuevo ciclo

DOCENTE QUE SE VA
  → Admin → Docentes → eliminar registro Teacher
  → Admin → Usuarios → desactivar o eliminar auth.User
```

### Funciones automáticas al aprobar

- **Contraseña temporal** generada de forma segura (10 caracteres aleatorios)
- **Username** generado desde cédula (o email si no hay cédula)
- Si hay número de WhatsApp configurado → credenciales enviadas automáticamente vía Evolution API
- Si ya existe usuario con esa cédula/email → se actualiza sin duplicar

### Página de Links (`/setup/links/`)

- Botones **📋 Copiar** para cada link
- Botones **WhatsApp** que abren `wa.me` con el link listo para enviar a contactos
- Contador de solicitudes pendientes en tiempo real
- Acceso directo a los paneles de revisión (admin / secretaría)

---

## Importación Masiva desde Google Sheets

Cada paso del wizard incluye un botón **📥 Importar** que abre un modal para cargar datos en masa. Soporta:

- **Google Sheets URL** (el sheet debe ser público o compartido como "Cualquier persona con el enlace puede ver")
- **Archivos CSV** (`.csv`)
- **Archivos Excel** (`.xlsx`, `.xls`)

### Cómo importar

1. En cualquier paso del wizard, haz click en **📥 Importar**
2. Selecciona la fuente: URL de Google Sheets o archivo
3. Click en **👁 Vista previa** para verificar los primeros 5 registros
4. Click en **🚀 Importar datos**

El sistema actualiza registros existentes (por cédula o email) y crea los nuevos. Los errores por fila se muestran como advertencias sin detener el proceso.

### Columnas esperadas por entidad

Los nombres de columna son flexibles: no distingue mayúsculas, tildes, ni espacios vs. guiones bajos.

#### Materias

| Columna | Requerida | Valores aceptados |
|---------|-----------|-------------------|
| `nombre` | ✅ | Nombre de la materia |
| `tipo` | — | `INSTRUMENTO`, `TEORIA`, `AGRUPACION` (default: INSTRUMENTO) |
| `descripcion` | — | Descripción libre |

**Ejemplo:**
```
nombre,tipo,descripcion
Piano,INSTRUMENTO,Instrumento de teclado
Solfeo,TEORIA,Lectura musical
Orquesta,AGRUPACION,
```

#### Tipos de Aporte

| Columna | Requerida | Descripción |
|---------|-----------|-------------|
| `nombre` | ✅ | Ej: "Trabajo en clase" |
| `codigo` | ✅ | Código único, ej: `TRABAJO` |
| `peso` | — | Peso relativo (default: 1.0) |
| `orden` | — | Orden de visualización (default: 0) |

**Ejemplo:**
```
nombre,codigo,peso,orden
Trabajo en clase,TRABAJO,1.0,1
Exposición,EXPO,1.5,2
Transcripción,TRANS,2.0,3
```

#### Niveles

| Columna | Requerida | Descripción |
|---------|-----------|-------------|
| `nivel` | ✅ | Número del 1 al 11, o nombre completo ("Básica 1") |
| `paralelo` | ✅ | Letra del paralelo (A, B, Único, etc.) |

**Ejemplo:**
```
nivel,paralelo
1,A
1,B
2,A
3,A
3,B
```

#### Docentes

| Columna | Requerida | Alternativas aceptadas |
|---------|-----------|------------------------|
| `nombre` | ✅ | `apellido_nombre`, `apellidos_nombres` |
| `cedula` | — | `ci`, `identificacion`, `id` |
| `email` | — | `correo`, `mail` |
| `telefono` | — | `celular`, `movil` |
| `especialidad` | — | `specialization`, `instrumento` |

> Se crea automáticamente un usuario de login. Contraseña por defecto: `Docente2025!`  
> Si el docente ya existe (misma cédula o email), se actualiza su información.

**Ejemplo:**
```
nombre,cedula,email,telefono,especialidad
García Juan,1234567890,juan@email.com,0987654321,Piano
Pérez María,,maria@email.com,,Solfeo
```

#### Estudiantes

| Columna | Requerida | Alternativas aceptadas |
|---------|-----------|------------------------|
| `nombre` | ✅ | `apellido_nombre`, `alumno`, `estudiante` |
| `cedula` | — | `ci`, `identificacion` |
| `email` | — | `correo` |
| `nivel` | — | `grado`, `curso` (número 1-11) |
| `paralelo` | — | `seccion`, `section`, `grupo` |
| `representante` | — | `nombre_representante`, `padre`, `madre` |
| `telefono_representante` | — | `tel_rep`, `celular_rep`, `whatsapp` |

> Contraseña por defecto para acceso: `Alumno2025!`

**Ejemplo:**
```
nombre,cedula,email,nivel,paralelo,representante,telefono_representante
López Ana,0987654321,ana@email.com,1,A,López Rosa,593987000001
Torres Luis,1234500000,,2,B,Torres Carmen,593998000002
```

#### Clases

| Columna | Requerida | Alternativas aceptadas |
|---------|-----------|------------------------|
| `nombre` | ✅ | `clase`, `name` |
| `materia` | ✅ | `subject`, `asignatura` |
| `docente` | — | `profesor`, `docente_email` |
| `nivel` | — | `level`, `grado` (número 1-11) |
| `paralelo` | — | `seccion`, `section` |
| `ciclo` | — | `ciclo_lectivo`, `periodo` (default: `2025-2026`) |

**Ejemplo:**
```
nombre,materia,docente,nivel,paralelo,ciclo
Piano I 2025-2026,Piano,García Juan,1,A,2025-2026
Solfeo Básica 2025,Solfeo,Pérez María,1,A,2025-2026
```

#### Matrículas

| Columna | Requerida | Alternativas aceptadas |
|---------|-----------|------------------------|
| `cedula_estudiante` | ✅ | `cedula`, `ci_estudiante`, `ci` |
| `nombre_clase` | ✅ | `clase`, `class` |

**Ejemplo:**
```
cedula_estudiante,nombre_clase
0987654321,Piano I 2025-2026
0987654321,Solfeo Básica 2025
1234500000,Piano I 2025-2026
```

### Endpoints de importación (API interna)

```
GET  /setup/importar/preview/?entity=<entidad>&url=<sheet_url>
POST /setup/importar/preview/?entity=<entidad>          (con archivo)
POST /setup/importar/<entidad>/                          (importa)
```

Entidades válidas: `materias`, `tipos_aporte`, `niveles`, `docentes`, `estudiantes`, `clases`, `matriculas`.

---

## Dashboard del Docente

Accesible en `/docente/` — exclusivo para usuarios con perfil de docente (`rol=DOCENTE` + `Teacher` profile).

### Características

- **Sidebar verde** con avatar, especialidad y lista de clases asignadas
- **Sub-navegación por clase**: Estudiantes → Calificaciones → Asistencia
- Acceso restringido: redirige a login si no es docente

### Secciones

#### Mi Dashboard (`/docente/`)
- Tarjetas de resumen: clases activas, total de estudiantes
- Acciones rápidas por clase

#### Detalle de clase (`/docente/clase/<pk>/`)
- Tabla completa de estudiantes inscritos
- Datos del representante (nombre + teléfono WhatsApp)
- Botones directos a Calificaciones y Asistencia

#### Calificaciones (`/docente/clase/<pk>/calificaciones/`)
- Selector de **Quimestre** (Q1 / Q2) y **Parcial** (1P / 2P / 3P / 4P)
- Tabla: filas = estudiantes, columnas = tipos de aporte configurados
- Notas con **código de color automático**:
  - 🟢 Verde: nota ≥ 7
  - 🟡 Amarillo: nota 5–6.9
  - 🔴 Rojo: nota < 5
- Guarda con `update_or_create` — no duplica calificaciones

#### Asistencia (`/docente/clase/<pk>/asistencia/`)
- Selector de fecha (calendario + fechas recientes con un click)
- Radio buttons: **Presente** / **Ausente** / **Justificado**
- Botones masivos "✓ Todos presentes" / "✗ Todos ausentes"
- Filas se colorean: verde (presente), rojo (ausente), amarillo (justificado)
- Guarda con `update_or_create` por fecha — editable en cualquier momento

---

## Admin Django organizado por jerarquía

El panel `/admin/` organiza los módulos según la **jerarquía natural de los datos**:

| Sección | Apps incluidas | Descripción |
|---------|---------------|-------------|
| ⚙️ **Configuración de la Institución** | `setup` | Datos institucionales, tipos de aporte |
| 📚 **Catálogo Académico** | `subjects`, `classes` | Materias, niveles, clases, calificaciones, asistencia |
| 👥 **Personal** | `teachers`, `students` | Docentes y estudiantes |
| 📝 **Matrículas** | `matriculas` | Solicitudes y matrículas en línea |
| 📊 **Comunicaciones** | `informes` | WhatsApp, informes, envíos |
| 🤖 **Agente IA** | `agente` | Alertas y recomendaciones automáticas |
| 🔑 **Sistema** | `users`, `auth`, `authtoken`, `django_celery_beat` | Usuarios, permisos, tareas |

El orden se controla en `config/admin_order.py` mediante monkey-patch de `AdminSite.get_app_list()`.

---

## Grupos de Niveles (Conservatorio)

Los niveles del conservatorio se agrupan así en toda la interfaz:

| Grupo | Niveles | Código DB |
|-------|---------|-----------|
| Básica — 1° y 2° | 1ero, 2do | `1`, `2` |
| Media — 3° al 5° | 3ero, 4to, 5to | `3`, `4`, `5` |
| Superior — 6° al 11° | 6to al 11vo | `6`, `7`, `8`, `9`, `10`, `11` |

El mapa ciclo → niveles está definido en `classes/models.py` (`GradeLevel._NIVEL_CICLO`).

---

## Comandos Makefile

```bash
make up            # Levantar todos los servicios
make down          # Detener
make build         # Reconstruir imágenes
make ps            # Estado de contenedores

make migrate       # Correr migraciones Django
make shell         # Django shell interactivo
make check         # Verificar configuración Django
make test          # Correr suite de tests

make etl-dry       # Preview ETL conservatorio.db → PostgreSQL
make etl           # ETL real

make api-logs      # Logs del servicio API
make wa-logs       # Logs del servicio WhatsApp
```

---

## ETL — Importar datos del conservatorio

El comando `import_from_conservatorio_db` migra docentes, cursos y tutores desde el SQLite histórico (`conservatorio.db`) a PostgreSQL:

```bash
make etl-dry    # Preview (sin cambios)
make etl        # Importar
```

Importa:
- **Docentes** → `Usuario(rol=DOCENTE)` + `Teacher`
- **Cursos** → `GradeLevel`
- **Asignaciones tutor-curso** → `GradeLevel.docente_tutor`

Para migración masiva desde Google Sheets / CSV / Excel, usar el **Wizard de Importación** en `/setup/`.

---

## API REST — Módulo informes

Todos los endpoints bajo `/api/informes/`:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `docentes/` | GET | Listado de docentes con aliases frontend |
| `docentes/upsert/` | POST | Crear o actualizar docente |
| `tutores-cursos/` | GET | Asignaciones tutor-curso |
| `grade-levels/` | GET | Listado de cursos |
| `subjects/` | GET | Listado de materias |
| `grades/` | GET | Calificaciones por curso/materia/período |
| `wa/instance/` | POST | Crear instancia Evolution API |
| `wa/status/<name>/` | GET | Estado de instancia WhatsApp |
| `wa/send/` | POST | Enviar mensaje individual |
| `wa/send-grades/` | POST | Envío masivo de informes a representantes |
| `wa/historial/` | GET | Historial de envíos WA |
| `forms/submit/` | POST | Enviar formulario(s) a Google Forms |
| `submissions/` | GET | Historial de submissions |
| `submissions/<pk>/resend/` | POST | Reenviar formulario |
| `submissions/<pk>/mark-wa-sent/` | POST | Marcar como enviado por WA |
| `sesiones/clase/<id>/` | GET | Sesiones de una clase |
| `sesiones/upsert/` | POST | Crear/actualizar sesión |
| `recomendaciones/upsert/` | POST | Crear/actualizar recomendación |

---

## Servicio WhatsApp (Node.js)

El servicio en `services/whatsapp/` actúa como:

1. **Servidor del frontend** — sirve `public/index.html` con la interfaz de informes
2. **Proxy a Django** — redirige `/api/informes/*` al backend Django (`SGA1_BASE`)
3. **Google Sheets** — operaciones de lectura/escritura de calificaciones
4. **Evolution API** — cliente WhatsApp

### Variables de entorno (`services/whatsapp/.env`)

```env
EVOLUTION_API_URL=https://tu-evolution-api.host
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE=NombreInstancia
OPENAI_API_KEY=sk-...
SGA1_BASE=http://api:8000
```

---

## Variables de Entorno

Archivo `.env` en la raíz del proyecto:

```env
# Base de datos
DB_NAME=music_registry_db
DB_USER=music_user
DB_PASSWORD=music_password
DB_HOST=db
DB_PORT=5432          # Usar 5434 si el puerto 5432 está ocupado en el host

# Django
SECRET_KEY=django-insecure-cambia-esto-en-produccion
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,sga1.12t4ag.easypanel.host

# Puertos del host (para evitar conflictos)
API_HOST_PORT=8002    # Puerto externo del contenedor api

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://tu-evolution-api.host
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE_NAME=NombreInstancia

# OpenAI
OPENAI_API_KEY=sk-...

# CSRF
CSRF_TRUSTED_ORIGINS=https://sga1.12t4ag.easypanel.host,http://localhost
```

---

## Modelo de Datos Principal

```
Usuario (identidad central — un único objeto por persona)
  ├── auth_user (OneToOne → django.contrib.auth.User)  ← acceso al sistema
  ├── Teacher   (OneToOne)  ← perfil de docente
  └── Student   (OneToOne)  ← perfil de estudiante

Jerarquía académica:
  Subject (materia)
    └── Clase (subject + grade_level + docente_base)
          └── Enrollment (clase + estudiante[Usuario] + docente)
                ├── CalificacionParcial (student + subject + quimestre + parcial + tipo_aporte)
                └── Asistencia (enrollment + fecha + estado)

GradeLevel (nivel + paralelo)  ← referenciado por Clase y Student

TipoAporte  ← referenciado por CalificacionParcial

informes app:
  ├── ConfiguracionWhatsapp   (instancias Evolution API)
  ├── RegistroEnvioWhatsapp   (historial mensajes WA)
  ├── SubmisionFormulario     (historial envíos Google Forms)
  ├── SesionClase             (sesiones con Google Sheets)
  └── RecomendacionEstudiante (recomendaciones por sesión)

setup app:
  └── ConfiguracionInstitucion (singleton — datos institucionales)
```

---

## Rutas principales del sistema

```
/                          → Landing pública
/users/login/              → Login
/users/logout/             → Logout
/admin/                    → Panel Admin Django (organizado por jerarquía)
/setup/                    → Wizard de Configuración (9 pasos)
/setup/importar/<entidad>/ → Importación masiva (POST)
/docente/                  → Dashboard del Docente
/docente/clase/<pk>/       → Detalle de clase
/docente/clase/<pk>/calificaciones/  → Ingreso de notas
/docente/clase/<pk>/asistencia/      → Control de asistencia
/graphql/                  → GraphQL endpoint
/api/informes/             → API REST de informes WhatsApp
/matriculas/               → Formularios públicos de matrícula
/healthz/                  → Health check (para Docker)
```

---

## Desarrollo Local

### Correr manage.py directamente

```bash
docker exec sga1_api python manage.py <comando>

# Ejemplos:
docker exec sga1_api python manage.py makemigrations
docker exec sga1_api python manage.py migrate
docker exec sga1_api python manage.py createsuperuser
docker exec sga1_api python manage.py shell
```

### Reiniciar el servicio api (recarga código Python)

```bash
docker compose restart api
```

> `docker compose restart` NO recarga el `.env`. Para cambios de variables de entorno usar:
> ```bash
> docker compose up -d api --force-recreate
> ```

### Traefik / Acceso externo

El sistema corre detrás de Traefik (Easypanel). La configuración de ruteo está en:
```
/etc/easypanel/traefik/config/sga1.yaml
```
Ruta: `sga1.12t4ag.easypanel.host` → `http://172.16.0.1:8001`

---

## Licencia

Uso interno — Conservatorio Bolívar de Ambato.
