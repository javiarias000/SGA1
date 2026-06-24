# Modelo de Datos del Sistema de Gestión Académica

Este documento describe las principales entidades de la base de datos, sus campos y las relaciones que existen entre ellas. El sistema utiliza un modelo de usuario centralizado en la aplicación `users` y extiende su funcionalidad en aplicaciones específicas como `teachers` y `students`.

---

## 1. Usuarios y Perfiles

### 1.1. `users.Usuario`
Este es el modelo **central** que representa a cualquier persona en el sistema académico. Unifica a docentes y estudiantes en una sola tabla para simplificar la autenticación y las relaciones.

- **Campos Clave:**
    - `nombre`: Nombre completo del usuario.
    - `rol`: Define si el usuario es `DOCENTE` o `ESTUDIANTE`.
    - `email`, `phone`, `cedula`: Datos de contacto e identificación.
    - `auth_user`: Relación **Uno-a-Uno** opcional con el modelo `User` de Django para permitir el inicio de sesión.

### 1.2. `teachers.Teacher`
Extiende a `users.Usuario` para añadir información específica de los docentes.

- **Relación:**
    - `usuario`: Vínculo **Uno-a-Uno** con `users.Usuario`.
- **Campos Clave:**
    - `specialization`: Especialidad del docente (ej. "Piano", "Teoría Musical").
    - `subjects`: Relación **Muchos-a-Muchos** con `subjects.Subject`, indica las materias que imparte.

### 1.3. `students.Student`
Extiende a `users.Usuario` para añadir información específica de los estudiantes.

- **Relación:**
    - `usuario`: Vínculo **Uno-a-Uno** con `users.Usuario`.
- **Campos Clave:**
    - `grade_level`: Relación **Muchos-a-Uno** con `classes.GradeLevel` (el curso al que pertenece).
    - `parent_name`, `parent_email`: Información del representante.

---

## 2. Estructura Académica

### 2.1. `subjects.Subject`
Representa una materia o asignatura que se puede impartir.

- **Campos Clave:**
    - `name`: Nombre único de la materia (ej. "Lenguaje Musical I", "Violín").
    - `tipo_materia`: Categoriza la materia (`INSTRUMENTO`, `TEORIA`, `AGRUPACION`).

### 2.2. `classes.GradeLevel`
Representa un curso o paralelo específico.

- **Campos Clave:**
    - `level`: El nivel del grado (ej. "Primero", "Segundo").
    - `section`: El paralelo (ej. "A", "B").
    - `docente_tutor`: Relación **Muchos-a-Uno** con `users.Usuario` para asignar un tutor al curso.

### 2.3. `classes.Clase`
Es la instancia de una materia para un ciclo lectivo. Es el eje sobre el cual giran las inscripciones y horarios.

- **Relaciones Clave:**
    - `subject`: Relación **Muchos-a-Uno** con `subjects.Subject` (la materia que se imparte).
    - `docente_base`: Relación **Muchos-a-Uno** con `users.Usuario` (el profesor principal de la clase).
    - `grade_level`: Relación **Muchos-a-Uno** opcional con `classes.GradeLevel`.

### 2.4. `classes.Enrollment` (Inscripción)
Es el modelo más importante para la lógica de negocio. Conecta a un estudiante con una clase específica y un docente.

- **Relaciones Clave:**
    - `estudiante`: Relación **Muchos-a-Uno** con `users.Usuario` (el estudiante inscrito).
    - `clase`: Relación **Muchos-a-Uno** con `classes.Clase` (la clase a la que se inscribe).
    - `docente`: Relación **Muchos-a-Uno** con `users.Usuario` (el docente asignado a este estudiante para esta clase, fundamental para clases de instrumento).

---

## 3. Calificaciones y Seguimiento

### 3.1. `classes.TipoAporte`
Define los tipos de calificaciones que se pueden registrar.
- **Campos Clave:**
    - `nombre`: "Deber", "Actuación en Clase", "Examen", etc.
    - `peso`: Ponderación del aporte para el cálculo de promedios.

### 3.2. `classes.CalificacionParcial`
Es el modelo unificado para registrar cada nota de un estudiante.

- **Relaciones Clave:**
    - `student`: Relación **Muchos-a-Uno** con `students.Student`.
    - `subject`: Relación **Muchos-a-Uno** con `subjects.Subject`.
    - `tipo_aporte`: Relación **Muchos-a-Uno** con `classes.TipoAporte`.
- **Campos Clave:**
    - `quimestre`: `Q1` o `Q2`.
    - `parcial`: `1P`, `2P`, `3P` o `4P`.
    - `calificacion`: La nota obtenida (0-10).

### 3.3. `classes.Asistencia`
Registra la asistencia de un estudiante a una clase.

- **Relación Clave:**
    - `inscripcion`: Relación **Muchos-a-Uno** con `classes.Enrollment`.
- **Campos Clave:**
    - `fecha`: El día de la asistencia.
    - `estado`: `Presente`, `Ausente`, `Justificado`.

### 3.4. `classes.Deber` y `classes.DeberEntrega`
Sistema para la gestión de tareas.

- **`Deber` (La Tarea):**
    - `teacher`: Relación **Muchos-a-Uno** con `users.Usuario` (quien asigna la tarea).
    - `clase`: Relación **Muchos-a-Uno** con `classes.Clase` (para qué clase es la tarea).
- **`DeberEntrega` (La Entrega):**
    - `deber`: Relación **Muchos-a-Uno** con `classes.Deber`.
    - `estudiante`: Relación **Muchos-a-Uno** con `users.Usuario`.
    - `calificacion`, `retroalimentacion`: La nota y comentarios del profesor.

---
## Resumen de Relaciones

```mermaid
erDiagram
    users_Usuario {
        string nombre
        string rol
        string email
        string cedula
    }

    teachers_Teacher {
        string specialization
    }

    students_Student {
        string parent_name
        string parent_email
    }

    subjects_Subject {
        string name
        string tipo_materia
    }

    classes_GradeLevel {
        string level
        string section
    }

    classes_Clase {
        string name
        string ciclo_lectivo
    }

    classes_Enrollment {
        string tipo_materia
        string estado
    }

    classes_CalificacionParcial {
        string quimestre
        string parcial
        decimal calificacion
    }

    users_Usuario ||--o{ teachers_Teacher : "es un"
    users_Usuario ||--o{ students_Student : "es un"
    users_Usuario {
        rol: "DOCENTE"
    } ||--o{ classes_GradeLevel : "es tutor de"
    users_Usuario {
        rol: "DOCENTE"
    } ||--o{ classes_Clase : "es docente base de"

    students_Student }o--|| classes_GradeLevel : "pertenece a"
    teachers_Teacher }o--|| subjects_Subject : "imparte"

    classes_Clase }o--|| subjects_Subject : "es de la materia"
    classes_Clase }o--|| classes_GradeLevel : "es para el nivel"

    classes_Enrollment }o--|| users_Usuario : "inscribe a (estudiante)"
    classes_Enrollment }o--|| classes_Clase : "en la clase"
    classes_Enrollment }o--|| users_Usuario : "con el docente (asignado)"

    classes_CalificacionParcial }o--|| students_Student : "califica a"
    classes_CalificacionParcial }o--|| subjects_Subject : "en la materia"

```
