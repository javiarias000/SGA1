# Plan: Evolution API + Tests + Bug Fixes

**Fecha:** 2026-04-13  
**Estado:** Pendiente de ejecución

---

## 0. Resumen ejecutivo

Tres frentes de trabajo:
1. **Evolution API** — Integrar envío de mensajes WhatsApp reemplazando/complementando `utils/notifications.py` (email)
2. **Tests** — Suite completa para REST endpoints y GraphQL mutations/queries
3. **Bugs** — 6 bugs concretos a corregir antes o durante los tests

---

## 1. Integración Evolution API (WhatsApp)

### 1.1. Variables de entorno requeridas

Agregar a `.env` y a `settings.py`:

```env
EVOLUTION_API_URL=https://tu-evolution-instance.com
EVOLUTION_API_KEY=tu_api_key
EVOLUTION_INSTANCE_NAME=conservatorio
```

En `settings.py`:
```python
EVOLUTION_API_URL = os.environ.get('EVOLUTION_API_URL', '')
EVOLUTION_API_KEY = os.environ.get('EVOLUTION_API_KEY', '')
EVOLUTION_INSTANCE_NAME = os.environ.get('EVOLUTION_INSTANCE_NAME', 'default')
```

### 1.2. Crear `utils/whatsapp.py`

Nuevo módulo que encapsula todos los llamados a Evolution API.

**Funciones a implementar:**

```python
class EvolutionAPI:
    """Cliente para Evolution API (WhatsApp)"""
    
    def send_text(self, number: str, text: str) -> bool:
        """
        POST /message/sendText/{instance}
        Body: {"number": "593XXXXXXXXX", "text": "..."}
        Headers: {"apikey": EVOLUTION_API_KEY}
        Retorna True si status 200/201, False en cualquier error.
        """
    
    def send_template(self, number: str, template_name: str, context: dict) -> bool:
        """
        Renderiza texto desde template string + context, llama send_text.
        """

# Instancia singleton
evolution = EvolutionAPI()
```

**Reglas de implementación:**
- Timeout de 10s en requests.post
- Log de errores con logger.error (no raise) para no romper flujo
- Formatear número: strip espacios/guiones, agregar prefijo 593 si no tiene código de país
- Si `EVOLUTION_API_URL` está vacío, log warning y retornar False (modo sin configurar)

### 1.3. Mensajes a implementar (mensajes concretos del conservatorio)

| Función | Trigger | Destinatario | Mensaje |
|---------|---------|--------------|---------|
| `notificar_reporte_calificaciones` | Manual o periódico | `Student.usuario.phone` o `Student.parent_phone` | Resumen de notas por quimestre |
| `notificar_alerta_bajo_rendimiento` | Al guardar `CalificacionParcial` < 7 | Representante | Alerta materia X con promedio Y |
| `notificar_reporte_mensual_docente` | Periódico (Celery beat) | `Teacher.usuario.auth_user.email` → phone via `Teacher.usuario.phone` | Reporte mensual de su grupo |
| `notificar_deber_asignado` | Al crear `Deber` | Estudiantes del grupo | "Nuevo deber: {titulo}, entrega: {fecha}" |
| `notificar_calificacion_deber` | Al calificar `DeberEntrega` | Estudiante | "Tu deber fue calificado: {nota}/10" |

### 1.4. Actualizar `utils/notifications.py`

Agregar clase `NotificacionWhatsApp` paralela a `NotificacionEmail`. Misma interfaz de métodos, diferente canal. Esto permite usar ambas a la vez si se desea.

```python
class NotificacionWhatsApp:
    @staticmethod
    def enviar_reporte_calificaciones(estudiante, phone): ...
    
    @staticmethod
    def enviar_alerta_bajo_rendimiento(estudiante, phone, materia): ...
    
    @staticmethod
    def enviar_reporte_mensual_docente(teacher, mes): ...
    
    @staticmethod
    def notificar_deber_asignado(clase, deber): ...
    
    @staticmethod
    def notificar_calificacion_deber(entrega): ...
```

### 1.5. Endpoint API para disparo manual

Nuevo endpoint REST en `academia/api/`:

```
POST /api/notificaciones/enviar-reporte/          → envía reporte calificaciones a un estudiante
POST /api/notificaciones/enviar-alerta/           → envía alerta bajo rendimiento
POST /api/notificaciones/test-whatsapp/           → envía mensaje de prueba (solo admin)
```

Serializador de request:
```json
{"estudiante_id": 42, "canal": "whatsapp"}
```

### 1.6. Hook en señales Django (automático)

En `classes/signals.py` (crear si no existe):
- `post_save` en `CalificacionParcial`: si nota < 7, disparar alerta WhatsApp al representante
- `post_save` en `DeberEntrega` con calificación: notificar al estudiante

---

## 2. Tests de endpoints

### 2.1. Archivo: `academia/tests/test_api_endpoints.py`

Tests REST con `APITestCase` de DRF.

**Endpoints a cubrir:**

| Endpoint | Método | Auth | Test cases |
|----------|--------|------|------------|
| `/api/token/auth/` | POST | — | credenciales válidas → 200 + token; inválidas → 400 |
| `/api/v1/students/` | GET | Token | lista retorna 200; sin auth → 401 |
| `/api/v1/students/{id}/` | GET | Token | existente → 200; inexistente → 404 |
| `/api/v1/teachers/` | GET | Token | lista retorna 200 |
| `/api/v1/teachers/{id}/` | GET | Token | existente → 200 |
| `/api/v1/clases/` | GET | Token | lista retorna 200 |
| `/api/v1/clases/{id}/` | GET | Token | existente → 200 |
| `/api/v1/enrollments/` | GET | Token | lista retorna 200 |
| `/api/v1/horarios/` | GET | Token | lista retorna 200 |
| `/api/notificaciones/test-whatsapp/` | POST | Admin Token | mock Evolution API → 200 |

**Fixtures a crear en `setUp`:**
```python
# 1 Usuario DOCENTE con auth_user
# 1 Teacher profile
# 1 GradeLevel
# 1 Subject (INSTRUMENTO)
# 1 Clase
# 1 Usuario ESTUDIANTE
# 1 Student profile
# 1 Enrollment
# 1 Horario
```

### 2.2. Archivo: `academia/tests/test_graphql.py`

Tests GraphQL con `graphene.test.Client`.

**Queries a testear:**
```graphql
{ allStudents { id usuario { nombre } } }
{ allTeachers { id usuario { nombre } } }
{ allSubjects { id name tipoMateria } }
{ allClases { id name subject { name } } }
{ allEnrollments { id estudiante { nombre } clase { name } } }
{ allGradeLevels { id level section } }
{ studentById(id: 1) { id usuario { nombre } } }
```

**Mutations a testear:**
```graphql
mutation { createSubject(name: "Test", tipoMateria: "TEORIA") { subject { id name } } }
mutation { createGradeLevel(level: "1", section: "A") { gradeLevel { id } } }
mutation { createOrUpdateUsuarioTeacher(nombre: "Docente Test") { usuario { id } teacher { id } } }
mutation { createOrUpdateUsuarioStudent(nombre: "Estudiante Test") { usuario { id } student { id } } }
mutation { createClase(name: "Clase Test", subjectId: "1", cicloLectivo: "2025-2026") { clase { id } } }
mutation { enrollStudentInClass(studentUsuarioId: "1", claseId: "1") { enrollment { id } } }
```

### 2.3. Archivo: `users/tests/test_auth.py`

```python
# Login con cedula (CustomBackend)
# Login con email
# Login inválido
# Obtener token via /api/token/auth/
# Acceso a vista protegida con @login_required
```

### 2.4. Archivo: `utils/tests/test_whatsapp.py`

```python
# Mock requests.post → 200 → send_text retorna True
# Mock requests.post → 500 → send_text retorna False
# Mock requests.post raise ConnectionError → retorna False
# EVOLUTION_API_URL vacío → retorna False sin hacer request
# Formateo de número: "0991234567" → "593991234567"
```

### 2.5. Ejecutar tests

```bash
# Todos
docker compose exec web python manage.py test

# Solo REST endpoints
docker compose exec web python manage.py test academia.tests.test_api_endpoints

# Solo GraphQL
docker compose exec web python manage.py test academia.tests.test_graphql

# Solo WhatsApp
docker compose exec web python manage.py test utils.tests.test_whatsapp
```

---

## 3. Bugs a corregir

### BUG-01: `notifications.py:139` — `teacher.user.email` no existe
**Archivo:** `utils/notifications.py:139`  
**Error:** `Teacher` no tiene campo `user`. Tiene `usuario` (FK a `Usuario`), y el email de login está en `usuario.auth_user.email`.  
**Fix:**
```python
# ANTES
to=[teacher.user.email]

# DESPUÉS
to=[teacher.usuario.auth_user.email] if teacher.usuario.auth_user else []
# + guardia: si no tiene email, saltar envío y logear warning
```

### BUG-02: `academia/serializers.py:9` — campo `display_name` no existe en `GradeLevel`
**Archivo:** `academia/serializers.py:9`  
**Error:** `GradeLevel` no define propiedad `display_name`. El serializer fallará al serializar.  
**Fix:**  
```python
# Opción A: usar SerializerMethodField
display_name = serializers.SerializerMethodField()
def get_display_name(self, obj): return str(obj)

# Opción B: simplificar a fields = ['id', 'level', 'section']
```

### BUG-03: `notifications.py:106` — `Student.objects.filter(teacher=teacher)` semántica incorrecta
**Archivo:** `utils/notifications.py:106`  
**Problema:** `Student.teacher` es FK a `Teacher`, pero la asignación real de docente-estudiante está en `Enrollment.docente`. Este método no obtiene los estudiantes que el docente enseña actualmente.  
**Fix:**
```python
# ANTES
estudiantes = Student.objects.filter(teacher=teacher, active=True)

# DESPUÉS — usar Enrollment para obtener estudiantes reales del docente
from classes.models import Enrollment
usuario_ids = Enrollment.objects.filter(
    docente=teacher.usuario, estado='ACTIVO'
).values_list('estudiante_id', flat=True).distinct()
estudiantes = Student.objects.filter(usuario_id__in=usuario_ids)
```

### BUG-04: `academia/serializers.py` — `HorarioSerializer.clase` serializa como `SubjectSerializer`
**Archivo:** `academia/serializers.py:19`  
**Problema:** `Horario.clase` es FK a `Subject`. Pero `SubjectSerializer` no es un nombre semántico claro aquí. No es bug de runtime pero sí confuso.  
**Fix:** Renombrar campo en serializer a `materia` con `source='clase'`, o renombrar el campo del modelo en una futura migración.

### BUG-05: `utils/notifications.py` — `CalificacionParcial().get_escala_cualitativa()` instancia sin datos
**Archivo:** `utils/notifications.py:34` y `:76`  
**Error:** `CalificacionParcial()` instancia el modelo sin argumentos, sin relaciones. Si `get_escala_cualitativa` depende del valor de `calificacion` en la instancia, retorna resultado inválido.  
**Fix:**
```python
# Verificar qué hace get_escala_cualitativa en classes/models.py
# Si es método de instancia que usa self.calificacion → convertir a @staticmethod o classmethod que reciba el valor
# Si ya maneja el caso de calificacion=None → documentar que es seguro
```

### BUG-06: Middleware deshabilitado — `RoleBasedAccessMiddleware` no corre
**Archivo:** `music_registry/settings.py:66`  
**Problema:** Control de acceso por rol no se aplica. Cualquier usuario autenticado puede acceder a rutas de docentes/admin.  
**Fix:** Re-habilitar los tres middlewares cuando se complete la migración GraphQL, o implementar `@role_required` decorators en vistas críticas como capa de seguridad alternativa.

---

## 4. Orden de ejecución recomendado

```
Semana 1:
  [ ] BUG-01 → fix teacher.user.email               (15 min, bajo riesgo)
  [ ] BUG-02 → fix display_name en serializer       (10 min, bajo riesgo)
  [ ] BUG-03 → fix Student.filter(teacher=) en notifs (20 min)
  [ ] BUG-05 → verificar get_escala_cualitativa      (30 min)

Semana 1-2:
  [ ] utils/whatsapp.py — cliente Evolution API     (2-3 hrs)
  [ ] NotificacionWhatsApp en notifications.py      (2 hrs)
  [ ] settings.py + .env vars                       (15 min)

Semana 2:
  [ ] Signals en classes/signals.py                 (1-2 hrs)
  [ ] Endpoints /api/notificaciones/                (2-3 hrs)
  [ ] academia/tests/test_api_endpoints.py          (3-4 hrs)
  [ ] academia/tests/test_graphql.py                (2-3 hrs)
  [ ] users/tests/test_auth.py                      (1-2 hrs)
  [ ] utils/tests/test_whatsapp.py                  (1-2 hrs)

Semana 3:
  [ ] BUG-06 — evaluar re-habilitar middlewares
  [ ] Correr suite completa, ajustar fallos
```

---

## 5. Dependencias externas

- `requests` — ya está en `requirements.txt` ✓
- Evolution API instance corriendo y accesible desde el contenedor Docker
- Número de WhatsApp registrado en la instancia Evolution

---

## 6. Consideraciones de diseño

- **No reemplazar email** — agregar WhatsApp como canal adicional. Ambos pueden correr en paralelo.
- **Fallos silenciosos** — envío WhatsApp nunca debe romper flujo de negocio (guardar nota, calificar deber). Siempre try/except con log.
- **Números de teléfono** — el campo `phone` en `Usuario` y `parent_phone` en `Student` no están validados. Agregar normalización al cliente Evolution antes de enviar.
- **Rate limiting** — Evolution API puede tener límites. Para envíos masivos (reporte mensual), usar tarea Celery con delay entre mensajes.
