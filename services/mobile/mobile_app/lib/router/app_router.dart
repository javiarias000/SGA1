import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../services/auth_service.dart';
import '../providers/auth_provider.dart';

// Auth
import '../screens/auth/login_screen.dart';
// Dashboard shell
import '../screens/dashboard/main_shell.dart';
// Students
import '../screens/students_list_screen.dart';
import '../screens/student_detail_screen.dart';
// Teachers
import '../screens/teachers_list_screen.dart';
import '../screens/teacher_detail_screen.dart';
// Subjects & Classes
import '../screens/subjects_list_screen.dart';
import '../screens/subject_detail_screen.dart';
import '../screens/horario_detail_screen.dart';
// Grades
import '../screens/grades/grades_screen.dart';
import '../screens/grades/grade_entry_screen.dart';
// Attendance
import '../screens/attendance/attendance_screen.dart';
import '../screens/attendance/mark_attendance_screen.dart';
// Deberes
import '../screens/deberes/deberes_screen.dart';
import '../screens/deberes/deber_form_screen.dart';
import '../screens/deberes/entregas_screen.dart';
// Registro
import '../screens/registro/registro_screen.dart';
// Notificaciones
import '../screens/notificaciones/notificaciones_screen.dart';
// Libreta
import '../screens/libreta/libreta_screen.dart';
// Matriculas
import '../screens/matriculas/nueva_matricula_screen.dart';
import '../screens/matriculas/confirmacion_screen.dart';
import '../screens/matriculas/seguimiento_screen.dart';
import '../screens/matriculas/secretaria_screen.dart';
// Agente
import '../screens/agente/alertas_screen.dart';
import '../screens/agente/alerta_detalle_screen.dart';
import '../screens/agente/informe_screen.dart';
// Profile
import '../screens/profile/profile_screen.dart';

class AppRouter {
  late final GoRouter router;
  final AuthService authService;
  final ApiService apiService;

  AppRouter({required this.authService, required this.apiService}) {
    router = GoRouter(
      initialLocation: '/',
      redirect: (context, state) async {
        final auth = context.read<AuthProvider>();
        final loggedIn = auth.isLoggedIn;
        final goingToLogin = state.matchedLocation == '/login';

        final isPublicPath = state.matchedLocation.startsWith('/matriculas/nueva') ||
            state.matchedLocation.startsWith('/matriculas/seguimiento') ||
            state.matchedLocation.startsWith('/matriculas/confirmacion');

        if (!loggedIn && !goingToLogin && !isPublicPath) return '/login';
        if (loggedIn && goingToLogin) return '/';
        return null;
      },
      errorBuilder: (context, state) => Scaffold(
        body: Center(child: Text('Error: ${state.error}')),
      ),
      routes: [
        // Auth
        GoRoute(path: '/login', name: 'login',
            builder: (_, __) => const LoginScreen()),

        // Main shell
        GoRoute(path: '/', name: 'home',
            builder: (_, __) => const MainShell()),

        // Grades
        GoRoute(path: '/grades', name: 'grades',
            builder: (_, __) => const GradesScreen()),
        GoRoute(path: '/grades/entry/:studentId', name: 'grade_entry',
            builder: (_, state) {
              final sid = int.parse(state.pathParameters['studentId']!);
              final name = state.uri.queryParameters['name'] ?? 'Estudiante';
              return GradeEntryScreen(studentId: sid, studentName: name);
            }),

        // Attendance
        GoRoute(path: '/attendance', name: 'attendance',
            builder: (_, __) => const AttendanceScreen()),
        GoRoute(path: '/attendance/marcar', name: 'mark_attendance',
            builder: (_, __) => const MarkAttendanceScreen()),

        // Deberes
        GoRoute(path: '/deberes', name: 'deberes',
            builder: (_, __) => const DeberesScreen()),
        GoRoute(path: '/deberes/nuevo', name: 'deber_nuevo',
            builder: (_, __) => const DeberFormScreen()),
        GoRoute(path: '/deberes/:deberId/entregas', name: 'deber_entregas',
            builder: (_, state) => EntregasScreen(
                deberId: int.parse(state.pathParameters['deberId']!))),

        // Registro de clases
        GoRoute(path: '/registro', name: 'registro',
            builder: (_, __) => const RegistroScreen()),

        // Notificaciones
        GoRoute(path: '/notificaciones', name: 'notificaciones',
            builder: (_, __) => const NotificacionesScreen()),

        // Libreta
        GoRoute(path: '/libreta/:studentId', name: 'libreta',
            builder: (_, state) {
              final sid = int.parse(state.pathParameters['studentId']!);
              final name = state.uri.queryParameters['name'] ?? 'Estudiante';
              return LibretaScreen(studentId: sid, studentName: name);
            }),

        // Profile
        GoRoute(path: '/profile', name: 'profile',
            builder: (_, __) => const ProfileScreen()),

        // Students
        GoRoute(path: '/students', name: 'students',
            builder: (_, __) => StudentsListScreen()),
        GoRoute(path: '/students/:studentId', name: 'student_detail',
            builder: (_, state) => StudentDetailScreen(
                studentId: int.parse(state.pathParameters['studentId']!))),

        // Teachers
        GoRoute(path: '/teachers', name: 'teachers',
            builder: (_, __) => TeachersListScreen()),
        GoRoute(path: '/teachers/:teacherId', name: 'teacher_detail',
            builder: (_, state) => TeacherDetailScreen(
                teacherId: int.parse(state.pathParameters['teacherId']!))),

        // Subjects & Classes
        GoRoute(path: '/subjects', name: 'subjects',
            builder: (_, __) => SubjectsListScreen()),
        GoRoute(path: '/subjects/:subjectId', name: 'subject_detail',
            builder: (_, state) => SubjectDetailScreen(
                subjectId: int.parse(state.pathParameters['subjectId']!))),
        GoRoute(path: '/classes', name: 'classes',
            builder: (_, __) => SubjectsListScreen()),
        GoRoute(path: '/horarios/:horarioId', name: 'horario_detail',
            builder: (_, state) => HorarioDetailScreen(
                horarioId: int.parse(state.pathParameters['horarioId']!))),

        // Matriculas
        GoRoute(path: '/matriculas/nueva', name: 'matriculas_nueva',
            builder: (_, __) => const NuevaMatriculaScreen()),
        GoRoute(path: '/matriculas/confirmacion', name: 'matriculas_confirmacion',
            builder: (_, state) {
              final codigo = state.uri.queryParameters['codigo'] ?? '';
              final nombre = state.uri.queryParameters['nombre'] ?? '';
              return ConfirmacionScreen(codigo: codigo, nombre: nombre);
            }),
        GoRoute(path: '/matriculas/seguimiento', name: 'matriculas_seguimiento',
            builder: (_, __) => const SeguimientoScreen()),
        GoRoute(path: '/matriculas/secretaria', name: 'matriculas_secretaria',
            builder: (_, __) => const SecretariaScreen()),

        // Agente IA
        GoRoute(path: '/agente/alertas', name: 'agente_alertas',
            builder: (_, __) => const AlertasScreen()),
        GoRoute(path: '/agente/alertas/:pk', name: 'agente_alerta_detalle',
            builder: (_, state) => AlertaDetalleScreen(
                alertaId: int.parse(state.pathParameters['pk']!))),
        GoRoute(path: '/agente/informes', name: 'agente_informes',
            builder: (_, __) => const InformeScreen()),
      ],
    );
  }
}
