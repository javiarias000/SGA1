import graphene
from graphene_django import DjangoObjectType
from users.models import Usuario
from students.models import Student
from teachers.models import Teacher
from subjects.models import Subject
from classes.models import GradeLevel, Clase, Enrollment

class UsuarioType(DjangoObjectType):
    class Meta:
        model = Usuario
        fields = ("id", "nombre", "rol", "email", "student_profile", "teacher_profile")

class StudentType(DjangoObjectType):
    class Meta:
        model = Student
        fields = ("id", "usuario", "grade_level", "parent_name", "active")

class TeacherType(DjangoObjectType):
    class Meta:
        model = Teacher
        fields = ("id", "usuario", "specialization", "subjects")

class SubjectType(DjangoObjectType):
    class Meta:
        model = Subject
        fields = ("id", "name", "description", "tipo_materia")

class GradeLevelType(DjangoObjectType):
    class Meta:
        model = GradeLevel
        fields = ("id", "level", "section", "docente_tutor")

class ClaseType(DjangoObjectType):
    class Meta:
        model = Clase
        fields = ("id", "name", "subject", "ciclo_lectivo", "paralelo", "docente_base", "description", "schedule", "room", "max_students", "active", "fecha", "grade_level", "periodo")

class EnrollmentType(DjangoObjectType):
    class Meta:
        model = Enrollment
        fields = ("id", "estudiante", "clase", "docente", "estado", "date_enrolled", "tipo_materia")

class CreateSubject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        tipo_materia = graphene.String(required=False)

    subject = graphene.Field(SubjectType)

    @staticmethod
    def mutate(root, info, name, description=None, tipo_materia=None):
        try:
            subject, created = Subject.objects.get_or_create(
                name=name,
                defaults={'description': description if description else '', 'tipo_materia': tipo_materia if tipo_materia else 'OTRO'}
            )
            # If not created, ensure fields are updated
            if not created:
                if description is not None and subject.description != description:
                    subject.description = description
                    subject.save()
                if tipo_materia is not None and subject.tipo_materia != tipo_materia:
                    subject.tipo_materia = tipo_materia
                    subject.save()
            return CreateSubject(subject=subject)
        except Exception as e:
            raise Exception(f"Error creating/updating subject: {e}")

class CreateGradeLevel(graphene.Mutation):
    class Arguments:
        level = graphene.String(required=True)
        section = graphene.String(required=True)

    grade_level = graphene.Field(GradeLevelType)

    @staticmethod
    def mutate(root, info, level, section):
        try:
            grade_level, created = GradeLevel.objects.get_or_create(
                level=level,
                section=section,
            )
            return CreateGradeLevel(grade_level=grade_level)
        except Exception as e:
            raise Exception(f"Error creating/updating GradeLevel: {e}")

class CreateOrUpdateUsuarioTeacher(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        email = graphene.String(required=False)
        phone = graphene.String(required=False)
        cedula = graphene.String(required=False)
        specialization = graphene.String(required=False)

    usuario = graphene.Field(UsuarioType)
    teacher = graphene.Field(TeacherType)

    @staticmethod
    def mutate(root, info, nombre, email=None, phone=None, cedula=None, specialization=None):
        usuario = None
        
        # Try to find Usuario by cedula, then email, then name
        if cedula:
            try:
                usuario = Usuario.objects.get(cedula=cedula)
            except Usuario.DoesNotExist:
                pass
        
        if not usuario and email:
            try:
                usuario = Usuario.objects.get(email=email)
            except Usuario.DoesNotExist:
                pass
        
        if not usuario:
            # If not found by unique fields, try by name and role
            try:
                usuario = Usuario.objects.get(nombre=nombre, rol=Usuario.Rol.DOCENTE)
            except Usuario.DoesNotExist:
                pass
        
        if usuario:
            # Update existing Usuario
            usuario.nombre = nombre
            usuario.rol = Usuario.Rol.DOCENTE
            if phone:
                usuario.phone = phone
            if cedula:
                usuario.cedula = cedula
            if email and (not usuario.email or usuario.email != email):
                # Only update email if it's new or different and doesn't conflict
                try:
                    # Check if email is already taken by another user
                    if Usuario.objects.filter(email=email).exclude(pk=usuario.pk).exists():
                        raise Exception(f"Email '{email}' is already taken by another user.")
                    usuario.email = email
                except Exception as e:
                    print(f"Warning: Could not update email for {nombre}: {e}")
            usuario.save()
            usuario_created = False
        else:
            # Create new Usuario
            try:
                usuario = Usuario.objects.create(
                    nombre=nombre,
                    rol=Usuario.Rol.DOCENTE,
                    email=email,
                    phone=phone,
                    cedula=cedula
                )
                usuario_created = True
            except Exception as e:
                # If email caused a unique constraint, try creating without email
                if 'email' in str(e).lower():
                    print(f"Warning: Failed to create Usuario with email '{email}'. Trying without email.")
                    usuario = Usuario.objects.create(
                        nombre=nombre,
                        rol=Usuario.Rol.DOCENTE,
                        phone=phone,
                        cedula=cedula
                    )
                    usuario_created = True
                else:
                    raise Exception(f"Error creating Usuario: {e}")

        # Create or update Teacher profile
        teacher, teacher_created = Teacher.objects.get_or_create(
            usuario=usuario,
            defaults={'specialization': specialization if specialization else ''}
        )
        if not teacher_created and specialization is not None and teacher.specialization != specialization:
            teacher.specialization = specialization
            teacher.save()

        return CreateOrUpdateUsuarioTeacher(usuario=usuario, teacher=teacher)

class CreateOrUpdateUsuarioStudent(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        email = graphene.String(required=False)
        phone = graphene.String(required=False)
        cedula = graphene.String(required=False)
        gradeLevelId = graphene.ID(required=False)
        parentName = graphene.String(required=False)
        parentPhone = graphene.String(required=False)

    usuario = graphene.Field(UsuarioType)
    student = graphene.Field(StudentType)

    @staticmethod
    def mutate(root, info, nombre, email=None, phone=None, cedula=None, gradeLevelId=None, parentName=None, parentPhone=None):
        usuario = None
        
        # Try to find Usuario by cedula, then email, then name
        if cedula:
            try:
                usuario = Usuario.objects.get(cedula=cedula)
            except Usuario.DoesNotExist:
                pass
        
        if not usuario and email:
            try:
                usuario = Usuario.objects.get(email=email)
            except Usuario.DoesNotExist:
                pass
        
        if not usuario:
            # If not found by unique fields, try by name and role
            try:
                usuario = Usuario.objects.get(nombre=nombre, rol=Usuario.Rol.ESTUDIANTE)
            except Usuario.DoesNotExist:
                pass
        
        if usuario:
            # Update existing Usuario
            usuario.nombre = nombre
            usuario.rol = Usuario.Rol.ESTUDIANTE
            if phone:
                usuario.phone = phone
            if cedula:
                usuario.cedula = cedula
            if email and (not usuario.email or usuario.email != email):
                try:
                    if Usuario.objects.filter(email=email).exclude(pk=usuario.pk).exists():
                        raise Exception(f"Email '{email}' is already taken by another user.")
                    usuario.email = email
                except Exception as e:
                    print(f"Warning: Could not update email for {nombre}: {e}")
            usuario.save()
            usuario_created = False
        else:
            # Create new Usuario
            try:
                usuario = Usuario.objects.create(
                    nombre=nombre,
                    rol=Usuario.Rol.ESTUDIANTE,
                    email=email,
                    phone=phone,
                    cedula=cedula
                )
                usuario_created = True
            except Exception as e:
                if 'email' in str(e).lower():
                    print(f"Warning: Failed to create Usuario with email '{email}'. Trying without email.")
                    usuario = Usuario.objects.create(
                        nombre=nombre,
                        rol=Usuario.Rol.ESTUDIANTE,
                        phone=phone,
                        cedula=cedula
                    )
                    usuario_created = True
                else:
                    raise Exception(f"Error creating Usuario: {e}")

        # Get GradeLevel object
        grade_level = None
        if gradeLevelId:
            try:
                grade_level = GradeLevel.objects.get(pk=gradeLevelId)
            except GradeLevel.DoesNotExist:
                pass # GradeLevel not found, student will be created without it

        # Create or update Student profile
        student, student_created = Student.objects.get_or_create(
            usuario=usuario,
            defaults={
                'grade_level': grade_level,
                'parent_name': parentName if parentName else '',
                'parent_phone': parentPhone if parentPhone else '',
            }
        )
        if not student_created:
            if grade_level and student.grade_level != grade_level:
                student.grade_level = grade_level
                student.save()
            if parentName is not None and student.parent_name != parentName:
                student.parent_name = parentName
                student.save()
            if parentPhone is not None and student.parent_phone != parentPhone:
                student.parent_phone = parentPhone
                student.save()

        return CreateOrUpdateUsuarioStudent(usuario=usuario, student=student)






from users.graphql.queries import Query as UserQuery

class Query(UserQuery, graphene.ObjectType):
    all_students = graphene.List(StudentType)
    student_by_id = graphene.Field(StudentType, id=graphene.Int())

    all_teachers = graphene.List(TeacherType)
    teacher_by_id = graphene.Field(TeacherType, id=graphene.Int())

    all_subjects = graphene.List(SubjectType)
    subject_by_id = graphene.Field(SubjectType, id=graphene.Int())

    all_clases = graphene.List(ClaseType)
    clase_by_id = graphene.Field(ClaseType, id=graphene.Int())

    all_enrollments = graphene.List(EnrollmentType)
    enrollment_by_id = graphene.Field(EnrollmentType, id=graphene.Int())

    all_grade_levels = graphene.List(GradeLevelType, level=graphene.String(), section=graphene.String())
    grade_level_by_id = graphene.Field(GradeLevelType, id=graphene.Int())

    def resolve_all_students(root, info):
        return Student.objects.select_related("usuario").all()

    def resolve_student_by_id(root, info, id):
        try:
            return Student.objects.select_related("usuario").get(pk=id)
        except Student.DoesNotExist:
            return None

    def resolve_all_teachers(root, info):
        return Teacher.objects.select_related("usuario").all()

    def resolve_teacher_by_id(root, info, id):
        try:
            return Teacher.objects.select_related("usuario").get(pk=id)
        except Teacher.DoesNotExist:
            return None

    def resolve_all_subjects(root, info):
        return Subject.objects.all()
    
    def resolve_subject_by_id(root, info, id):
        try:
            return Subject.objects.get(pk=id)
        except Subject.DoesNotExist:
            return None

    def resolve_all_clases(root, info):
        return Clase.objects.select_related("subject", "docente_base", "grade_level").all()
    
    def resolve_clase_by_id(root, info, id):
        try:
            return Clase.objects.select_related("subject", "docente_base", "grade_level").get(pk=id)
        except Clase.DoesNotExist:
            return None

    def resolve_all_enrollments(root, info):
        return Enrollment.objects.select_related("estudiante", "clase", "docente").all()

    def resolve_enrollment_by_id(root, info, id):
        try:
            return Enrollment.objects.select_related("estudiante", "clase", "docente").get(pk=id)
        except Enrollment.DoesNotExist:
            return None

    def resolve_all_grade_levels(root, info, level=None, section=None):
        queryset = GradeLevel.objects.select_related("docente_tutor").all()
        if level:
            queryset = queryset.filter(level=level)
        if section:
            queryset = queryset.filter(section=section)
        return queryset

    def resolve_grade_level_by_id(root, info, id):
        try:
            return GradeLevel.objects.select_related("docente_tutor").get(pk=id)
        except GradeLevel.DoesNotExist:
            return None

class AssignDocenteBaseToClase(graphene.Mutation):
    class Arguments:
        clase_id = graphene.ID(required=True)
        docente_id = graphene.ID(required=True)

    clase = graphene.Field(ClaseType)

    def mutate(self, info, clase_id, docente_id):
        try:
            clase = Clase.objects.get(pk=clase_id)
            docente = Usuario.objects.get(pk=docente_id, rol=Usuario.Rol.DOCENTE)
            clase.docente_base = docente
            clase.save()
            return AssignDocenteBaseToClase(clase=clase)
        except Clase.DoesNotExist:
            raise Exception("Clase not found")
        except Usuario.DoesNotExist:
            raise Exception("Docente not found or user is not a teacher")

class AssignSubjectsToTeacher(graphene.Mutation):
    class Arguments:
        teacher_id = graphene.ID(required=True)
        subject_ids = graphene.List(graphene.ID, required=True)

    teacher = graphene.Field(TeacherType)

    def mutate(self, info, teacher_id, subject_ids):
        try:
            teacher = Teacher.objects.get(pk=teacher_id)
        except Teacher.DoesNotExist:
            raise Exception("Teacher not found")

        subjects = []
        for s_id in subject_ids:
            try:
                subject = Subject.objects.get(pk=s_id)
                subjects.append(subject)
            except Subject.DoesNotExist:
                raise Exception(f"Subject with ID {s_id} not found")
        
        teacher.subjects.set(subjects) # Reassign all subjects
        
        return AssignSubjectsToTeacher(teacher=teacher)

class EnrollStudentInClass(graphene.Mutation):
    class Arguments:
        student_usuario_id = graphene.ID(required=True)
        clase_id = graphene.ID(required=True)
        docente_usuario_id = graphene.ID(required=False) # Docente might be null

    enrollment = graphene.Field(EnrollmentType)

    def mutate(self, info, student_usuario_id, clase_id, docente_usuario_id=None):
        try:
            student_usuario = Usuario.objects.get(pk=student_usuario_id, rol=Usuario.Rol.ESTUDIANTE)
        except Usuario.DoesNotExist:
            raise Exception("Student Usuario not found or user is not a student")
        
        try:
            clase = Clase.objects.get(pk=clase_id)
        except Clase.DoesNotExist:
            raise Exception("Clase not found")
        
        docente_usuario = None
        if docente_usuario_id:
            try:
                docente_usuario = Usuario.objects.get(pk=docente_usuario_id, rol=Usuario.Rol.DOCENTE)
            except Usuario.DoesNotExist:
                raise Exception("Docente Usuario not found or user is not a teacher")
        
        enrollment, created = Enrollment.objects.get_or_create(
            estudiante=student_usuario,
            clase=clase,
            defaults={'docente': docente_usuario, 'estado': 'ACTIVO'}
        )
        
        if not created and enrollment.docente != docente_usuario:
            enrollment.docente = docente_usuario
            enrollment.save(update_fields=['docente'])

        return EnrollStudentInClass(enrollment=enrollment)

class CreateClase(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        subject_id = graphene.ID(required=True)
        ciclo_lectivo = graphene.String(required=True)
        docente_base_id = graphene.ID(required=False)
        description = graphene.String(required=False)

    clase = graphene.Field(ClaseType)

    def mutate(self, info, name, subject_id, ciclo_lectivo, docente_base_id=None, description=""):
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            raise Exception(f"Subject with ID {subject_id} not found")
        
        docente_base = None
        if docente_base_id:
            try:
                docente_base = Usuario.objects.get(pk=docente_base_id, rol=Usuario.Rol.DOCENTE)
            except Usuario.DoesNotExist:
                raise Exception(f"Docente Usuario with ID {docente_base_id} not found or user is not a teacher")
        
        clase, created = Clase.objects.get_or_create(
            name=name,
            subject=subject,
            ciclo_lectivo=ciclo_lectivo,
            defaults={
                'docente_base': docente_base,
                'description': description,
                # Set other default fields for Clase if necessary
                'active': True,
            }
        )
        
        # If the clase already existed but docente_base was not set or different
        if not created and docente_base and clase.docente_base != docente_base:
            clase.docente_base = docente_base
            clase.save(update_fields=['docente_base'])

        return CreateClase(clase=clase)


from users.graphql.schema import UserMutations
class Mutation(UserMutations,graphene.ObjectType):
    assign_docente_base_to_clase = AssignDocenteBaseToClase.Field()
    assign_subjects_to_teacher = AssignSubjectsToTeacher.Field()
    enroll_student_in_class = EnrollStudentInClass.Field()
    create_clase = CreateClase.Field()

    create_subject = CreateSubject.Field()
    create_grade_level = CreateGradeLevel.Field()
    create_or_update_usuario_teacher = CreateOrUpdateUsuarioTeacher.Field()
    create_or_update_usuario_student = CreateOrUpdateUsuarioStudent.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
