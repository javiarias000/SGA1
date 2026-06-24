import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'api/api_service.dart';
import 'core/theme.dart';
import 'providers/auth_provider.dart';
import 'providers/horario_provider.dart';
import 'providers/student_provider.dart';
import 'providers/teacher_provider.dart';
import 'providers/clase_provider.dart';
import 'providers/subject_provider.dart';
import 'providers/enrollment_provider.dart';
import 'providers/grade_provider.dart';
import 'providers/attendance_provider.dart';
import 'providers/tipo_aporte_provider.dart';
import 'providers/deber_provider.dart';
import 'providers/activity_provider.dart';
import 'router/app_router.dart';
import 'services/auth_service.dart';

void main() {
  final apiService = ApiService();
  final authService = AuthService(apiService);

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => apiService),
        Provider<AuthService>(create: (_) => authService),
        ChangeNotifierProvider<AuthProvider>(
          create: (_) => AuthProvider(authService),
        ),
        ChangeNotifierProxyProvider<AuthProvider, HorarioProvider>(
          create: (ctx) => HorarioProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => HorarioProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, StudentProvider>(
          create: (ctx) => StudentProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => StudentProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, TeacherProvider>(
          create: (ctx) => TeacherProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => TeacherProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, ClaseProvider>(
          create: (ctx) => ClaseProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => ClaseProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, SubjectProvider>(
          create: (ctx) => SubjectProvider(
            ctx.read<ClaseProvider>(), ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => SubjectProvider(
            ctx.read<ClaseProvider>(), ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, EnrollmentProvider>(
          create: (ctx) => EnrollmentProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => EnrollmentProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, GradeProvider>(
          create: (ctx) => GradeProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => GradeProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, AttendanceProvider>(
          create: (ctx) => AttendanceProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => AttendanceProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, TipoAporteProvider>(
          create: (ctx) => TipoAporteProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => TipoAporteProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, DeberProvider>(
          create: (ctx) => DeberProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => DeberProvider(ctx.read<ApiService>(), auth),
        ),
        ChangeNotifierProxyProvider<AuthProvider, ActivityProvider>(
          create: (ctx) => ActivityProvider(ctx.read<ApiService>(), ctx.read<AuthProvider>()),
          update: (ctx, auth, _) => ActivityProvider(ctx.read<ApiService>(), auth),
        ),
      ],
      child: MyApp(authService: authService),
    ),
  );
}

class MyApp extends StatelessWidget {
  final AuthService authService;
  const MyApp({super.key, required this.authService});

  @override
  Widget build(BuildContext context) {
    final router = AppRouter(
      authService: authService,
      apiService: context.read<ApiService>(),
    );
    return MaterialApp.router(
      title: 'Conservatorio Bolívar',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      routerConfig: router.router,
    );
  }
}
