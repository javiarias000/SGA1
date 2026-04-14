import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/auth_provider.dart';
import 'package:mobile_app/api/api_service.dart'; // Import ApiService
import 'package:mobile_app/services/auth_service.dart'; // Import AuthService
import 'package:mobile_app/main.dart'; // Import main.dart for LoginScreen and MyHomePage

// Import the screens that are used in the router
import 'package:mobile_app/screens/students_list_screen.dart';
import 'package:mobile_app/screens/teachers_list_screen.dart';
import 'package:mobile_app/screens/subjects_list_screen.dart';
import 'package:mobile_app/screens/student_detail_screen.dart';
import 'package:mobile_app/screens/teacher_detail_screen.dart';
import 'package:mobile_app/screens/horario_detail_screen.dart';
import 'package:mobile_app/screens/subject_detail_screen.dart'; // Import SubjectDetailScreen

class AppRouter {
  late final GoRouter router;
  final AuthService authService;
  final ApiService apiService;

  AppRouter({required this.authService, required this.apiService}) {
    router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          name: 'home',
          builder: (context, state) => MyHomePage(title: 'Horarios'),
        ),
        GoRoute(
          path: '/login',
          name: 'login',
          builder: (context, state) => LoginScreen(),
        ),
        GoRoute(
          path: '/students',
          name: 'students',
          builder: (context, state) => StudentsListScreen(),
        ),
        GoRoute(
          path: '/teachers',
          name: 'teachers',
          builder: (context, state) => TeachersListScreen(),
        ),
        GoRoute(
          path: '/subjects',
          name: 'subjects',
          builder: (context, state) => SubjectsListScreen(),
        ),
        GoRoute(
          path: '/students/:studentId',
          name: 'student_detail',
          builder: (context, state) {
            final studentId = int.parse(state.pathParameters['studentId']!);
            return StudentDetailScreen(studentId: studentId);
          },
        ),
        GoRoute(
          path: '/teachers/:teacherId',
          name: 'teacher_detail',
          builder: (context, state) {
            final teacherId = int.parse(state.pathParameters['teacherId']!);
            return TeacherDetailScreen(teacherId: teacherId);
          },
        ),
        GoRoute(
          path: '/horarios/:horarioId',
          name: 'horario_detail',
          builder: (context, state) {
            final horarioId = int.parse(state.pathParameters['horarioId']!);
            return HorarioDetailScreen(horarioId: horarioId);
          },
        ),
        GoRoute(
          path: '/subjects/:subjectId',
          name: 'subject_detail',
          builder: (context, state) {
            final subjectId = int.parse(state.pathParameters['subjectId']!);
            return SubjectDetailScreen(subjectId: subjectId);
          },
        ),
      ],
      redirect: (context, state) async {
        final authProvider = context.read<AuthProvider>();
        final loggedIn = authProvider.isLoggedIn;
        final role = authProvider.userRole;
        final goingToLogin = state.matchedLocation == '/login';

        if (!loggedIn && !goingToLogin) {
          return '/login';
        }
        if (loggedIn && goingToLogin) {
          return '/';
        }

        // Role-based access control
        if (role == 'ESTUDIANTE') {
          if (state.matchedLocation == '/teachers' ||
              state.matchedLocation == '/subjects' ||
              state.matchedLocation.startsWith('/teachers/') ||
              state.matchedLocation.startsWith('/subjects/')) {
            return '/'; // Redirect students away from admin/teacher views
          }
        }

        return null;
      },
      errorBuilder: (context, state) => Scaffold(
        body: Center(
          child: Text('Error: ${state.error}'),
        ),
      ),
    );
  }
}