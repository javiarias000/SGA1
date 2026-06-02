import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/grade_provider.dart';
import '../../providers/attendance_provider.dart';
import '../../widgets/common_widgets.dart';

class StudentDashboard extends StatefulWidget {
  const StudentDashboard({super.key});

  @override
  State<StudentDashboard> createState() => _StudentDashboardState();
}

class _StudentDashboardState extends State<StudentDashboard> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  void _loadData() {
    final auth = context.read<AuthProvider>();
    if (auth.studentId != null) {
      context.read<GradeProvider>().fetchGrades(auth.studentId!);
      context.read<AttendanceProvider>().fetchAttendance(auth.studentId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final grades = context.watch<GradeProvider>();
    final attend = context.watch<AttendanceProvider>();

    final nombre = auth.userName ?? 'Estudiante';
    final promedioGeneral = grades.promedioGeneral;
    final totalClases = attend.totalClases;
    final presentes = attend.presentes;
    final pctAsistencia = totalClases > 0 ? (presentes / totalClases * 100) : 0.0;

    return Scaffold(
      backgroundColor: AppColors.surface,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 160,
            floating: false,
            pinned: true,
            backgroundColor: AppColors.primary,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [AppColors.primary, AppColors.primary700],
                    begin: Alignment.topLeft, end: Alignment.bottomRight,
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        const Text('Bienvenido 👋', style: TextStyle(color: Colors.white60, fontSize: 13)),
                        Text(nombre,
                            style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                        Text(auth.userRole ?? '', style: const TextStyle(color: Colors.white54, fontSize: 12)),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.logout, color: Colors.white),
                onPressed: () async {
                  await context.read<AuthProvider>().logout();
                  if (mounted) context.go('/login');
                },
              ),
            ],
          ),

          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Stats
                  Row(children: [
                    Expanded(
                      child: StatCard(
                        label: 'Promedio General',
                        value: promedioGeneral != null
                            ? promedioGeneral.toStringAsFixed(2)
                            : '—',
                        icon: Icons.bar_chart,
                        color: _colorNota(promedioGeneral),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: StatCard(
                        label: 'Asistencia',
                        value: '${pctAsistencia.toStringAsFixed(0)}%',
                        icon: Icons.event_available,
                        color: pctAsistencia >= 80 ? AppColors.success : AppColors.warning,
                      ),
                    ),
                  ]),

                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Acceso rápido'),

                  _QuickAction(
                    icon: Icons.grade,
                    title: 'Mis Calificaciones',
                    subtitle: 'Ver notas por materia y parcial',
                    color: AppColors.primary,
                    onTap: () => context.push('/grades'),
                  ),
                  const SizedBox(height: 10),
                  _QuickAction(
                    icon: Icons.event_note,
                    title: 'Mi Asistencia',
                    subtitle: '$presentes de $totalClases clases asistidas',
                    color: AppColors.success,
                    onTap: () => context.push('/attendance'),
                  ),
                  const SizedBox(height: 10),
                  _QuickAction(
                    icon: Icons.school_outlined,
                    title: 'Renovar Matrícula',
                    subtitle: 'Ciclo lectivo actual',
                    color: AppColors.gold,
                    onTap: () => context.push('/matriculas/nueva'),
                  ),

                  if (grades.isLoading || attend.isLoading) ...[
                    const SizedBox(height: 20),
                    const LoadingWidget(message: 'Cargando datos...'),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _colorNota(double? nota) {
    if (nota == null) return AppColors.textMuted;
    if (nota >= 9) return AppColors.dar;
    if (nota >= 7) return AppColors.aar;
    if (nota > 4) return AppColors.paar;
    return AppColors.naar;
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;
  const _QuickAction({
    required this.icon, required this.title, required this.subtitle,
    required this.color, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
        onTap: onTap,
      ),
    );
  }
}
