import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/student_provider.dart';
import '../../widgets/common_widgets.dart';

class TeacherDashboard extends StatefulWidget {
  const TeacherDashboard({super.key});

  @override
  State<TeacherDashboard> createState() => _TeacherDashboardState();
}

class _TeacherDashboardState extends State<TeacherDashboard> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<StudentProvider>().fetchStudents();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final students = context.watch<StudentProvider>();
    final nombre = auth.userName ?? 'Docente';

    return Scaffold(
      backgroundColor: AppColors.surface,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 160,
            pinned: true,
            backgroundColor: AppColors.primary,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [AppColors.primary, Color(0xFF0056CC)],
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
                        const Text('Panel Docente', style: TextStyle(color: Colors.white60, fontSize: 13)),
                        Text(nombre,
                            style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                        const Text('Docente', style: TextStyle(color: Colors.white54, fontSize: 12)),
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
                        label: 'Mis Estudiantes',
                        value: students.isLoading ? '...' : '${students.students.length}',
                        icon: Icons.people,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: StatCard(
                        label: 'Alertas IA',
                        value: '—',
                        icon: Icons.notifications_active,
                        color: AppColors.warning,
                      ),
                    ),
                  ]),

                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Gestión académica'),

                  _action(Icons.people, 'Mis Estudiantes', 'Listado y detalle de cada estudiante',
                      AppColors.primary, () => context.push('/students')),
                  const SizedBox(height: 10),
                  _action(Icons.grade, 'Ingresar Calificaciones',
                      'Registrar notas por parcial y quimestre', AppColors.aar,
                      () => context.push('/grades')),
                  const SizedBox(height: 10),
                  _action(Icons.event_note, 'Registrar Asistencia',
                      'Marcar presente / ausente por clase', AppColors.success,
                      () => context.push('/attendance')),
                  const SizedBox(height: 10),
                  _action(Icons.class_, 'Mis Clases', 'Ver clases asignadas', AppColors.primary700,
                      () => context.push('/classes')),

                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Herramientas IA'),

                  _action(Icons.notifications_active, 'Panel de Alertas',
                      'Estudiantes con bajo rendimiento', const Color(0xFFEA580C),
                      () => context.push('/agente/alertas')),
                  const SizedBox(height: 10),
                  _action(Icons.edit_note, 'Asistente de Informes',
                      'Mejorar redacción de informes de clase', AppColors.primary600,
                      () => context.push('/agente/informes')),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _action(IconData icon, String title, String sub, Color color, VoidCallback onTap) {
    return Card(
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text(sub, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
        onTap: onTap,
      ),
    );
  }
}
