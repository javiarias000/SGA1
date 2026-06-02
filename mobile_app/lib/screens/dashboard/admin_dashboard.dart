import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/student_provider.dart';
import '../../providers/teacher_provider.dart';
import '../../widgets/common_widgets.dart';

class AdminDashboard extends StatefulWidget {
  const AdminDashboard({super.key});

  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends State<AdminDashboard> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<StudentProvider>().fetchStudents();
      context.read<TeacherProvider>().fetchTeachers();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final students = context.watch<StudentProvider>();
    final teachers = context.watch<TeacherProvider>();

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
                    colors: [Color(0xFF000d1f), AppColors.primary],
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
                        const Text('Panel Administrativo', style: TextStyle(color: Colors.white60, fontSize: 13)),
                        Text(auth.userName ?? 'Administrador',
                            style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                        const Text('Administrador', style: TextStyle(color: Colors.white54, fontSize: 12)),
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
                  // Stats grid
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 1.5,
                    children: [
                      StatCard(
                        label: 'Estudiantes',
                        value: students.isLoading ? '...' : '${students.students.length}',
                        icon: Icons.people,
                        color: AppColors.primary,
                      ),
                      StatCard(
                        label: 'Docentes',
                        value: teachers.isLoading ? '...' : '${teachers.teachers.length}',
                        icon: Icons.school,
                        color: AppColors.aar,
                      ),
                      StatCard(
                        label: 'Matrículas',
                        value: '—',
                        icon: Icons.assignment,
                        color: AppColors.gold,
                      ),
                      StatCard(
                        label: 'Alertas IA',
                        value: '—',
                        icon: Icons.notifications_active,
                        color: AppColors.error,
                      ),
                    ],
                  ),

                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Gestión académica'),
                  _action(Icons.people, 'Estudiantes', 'Listado, perfiles y matrículas',
                      AppColors.primary, () => context.push('/students')),
                  const SizedBox(height: 10),
                  _action(Icons.school, 'Docentes', 'Gestionar cuerpo docente',
                      AppColors.aar, () => context.push('/teachers')),
                  const SizedBox(height: 10),
                  _action(Icons.class_, 'Clases', 'Clases y materias del ciclo',
                      AppColors.primary700, () => context.push('/classes')),

                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Matrículas en línea'),
                  _action(Icons.add_circle_outline, 'Nueva inscripción',
                      'Formulario de matrícula público', AppColors.success,
                      () => context.push('/matriculas/nueva')),
                  const SizedBox(height: 10),
                  _action(Icons.search, 'Seguimiento', 'Estado de solicitud por código o cédula',
                      AppColors.primary600, () => context.push('/matriculas/seguimiento')),
                  const SizedBox(height: 10),
                  _action(Icons.admin_panel_settings, 'Secretaría',
                      'Revisar y aprobar solicitudes', AppColors.warning,
                      () => context.push('/matriculas/secretaria')),

                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Agente IA'),
                  _action(Icons.notifications_active, 'Alertas académicas',
                      'Estudiantes en riesgo detectados por IA', const Color(0xFFEA580C),
                      () => context.push('/agente/alertas')),
                  const SizedBox(height: 10),
                  _action(Icons.edit_note, 'Asistente de informes',
                      'Mejorar informes docentes con IA', AppColors.primary,
                      () => context.push('/agente/informes')),
                  const SizedBox(height: 24),
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
