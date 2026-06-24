import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import 'student_dashboard.dart';
import 'teacher_dashboard.dart';
import 'admin_dashboard.dart';
import '../grades/grades_screen.dart';
import '../attendance/attendance_screen.dart';
import '../profile/profile_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  List<_NavItem> _navItems(String role) {
    if (role == 'ESTUDIANTE') {
      return [
        _NavItem(Icons.dashboard_outlined, Icons.dashboard, 'Inicio'),
        _NavItem(Icons.grade_outlined, Icons.grade, 'Notas'),
        _NavItem(Icons.event_note_outlined, Icons.event_note, 'Asistencia'),
        _NavItem(Icons.assignment_outlined, Icons.assignment, 'Deberes'),
        _NavItem(Icons.person_outline, Icons.person, 'Perfil'),
      ];
    }
    if (role == 'DOCENTE') {
      return [
        _NavItem(Icons.dashboard_outlined, Icons.dashboard, 'Inicio'),
        _NavItem(Icons.people_outline, Icons.people, 'Estudiantes'),
        _NavItem(Icons.school_outlined, Icons.school, 'Académico'),
        _NavItem(Icons.smart_toy_outlined, Icons.smart_toy, 'IA'),
        _NavItem(Icons.person_outline, Icons.person, 'Perfil'),
      ];
    }
    // ADMIN / STAFF
    return [
      _NavItem(Icons.dashboard_outlined, Icons.dashboard, 'Inicio'),
      _NavItem(Icons.people_outline, Icons.people, 'Estudiantes'),
      _NavItem(Icons.assignment_outlined, Icons.assignment, 'Matrículas'),
      _NavItem(Icons.smart_toy_outlined, Icons.smart_toy, 'IA'),
      _NavItem(Icons.person_outline, Icons.person, 'Perfil'),
    ];
  }

  Widget _buildPage(String role, int index) {
    if (role == 'ESTUDIANTE') {
      switch (index) {
        case 0: return const StudentDashboard();
        case 1: return const GradesScreen();
        case 2: return const AttendanceScreen();
        case 3: return _buildEstudianteDeberesTab();
        default: return const ProfileScreen();
      }
    }
    if (role == 'DOCENTE') {
      switch (index) {
        case 0: return const TeacherDashboard();
        case 1: return _buildStudentsTab();
        case 2: return _buildDocenteAcademicoTab();
        case 3: return _buildAgentTab();
        default: return const ProfileScreen();
      }
    }
    // Admin
    switch (index) {
      case 0: return const AdminDashboard();
      case 1: return _buildStudentsTab();
      case 2: return _buildMatriculasTab();
      case 3: return _buildAgentTab();
      default: return const ProfileScreen();
    }
  }

  Widget _buildStudentsTab() {
    return Scaffold(
      appBar: AppBar(title: const Text('Estudiantes')),
      body: Center(
        child: ElevatedButton.icon(
          onPressed: () => context.push('/students'),
          icon: const Icon(Icons.people),
          label: const Text('Ver listado completo'),
        ),
      ),
    );
  }

  Widget _buildEstudianteDeberesTab() {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis Deberes')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        _dashCard(Icons.assignment, 'Mis Deberes',
            'Ver deberes asignados y estado de entregas',
            AppColors.primary, () => context.push('/deberes')),
        const SizedBox(height: 10),
        _dashCard(Icons.book, 'Mi Libreta',
            'Ver todas mis calificaciones y asistencia',
            AppColors.aar, () {
          final auth = context.read<AuthProvider>();
          if (auth.studentId != null) {
            context.push('/libreta/${auth.studentId}?name=${Uri.encodeComponent(auth.userName ?? '')}');
          }
        }),
      ]),
    );
  }

  Widget _buildDocenteAcademicoTab() {
    return Scaffold(
      appBar: AppBar(title: const Text('Académico')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        _dashCard(Icons.grade, 'Calificaciones',
            'Ver e ingresar notas por parcial', AppColors.aar,
            () => context.push('/grades')),
        const SizedBox(height: 10),
        _dashCard(Icons.event_note, 'Ver Asistencia',
            'Historial de asistencia por estudiante', AppColors.primary,
            () => context.push('/attendance')),
        const SizedBox(height: 10),
        _dashCard(Icons.checklist, 'Marcar Asistencia',
            'Registrar presente/ausente de hoy', AppColors.success,
            () => context.push('/attendance/marcar')),
        const SizedBox(height: 10),
        _dashCard(Icons.assignment, 'Deberes',
            'Crear y gestionar tareas', AppColors.warning,
            () => context.push('/deberes')),
        const SizedBox(height: 10),
        _dashCard(Icons.event_repeat, 'Registro de Clases',
            'Registrar actividad de cada sesión', AppColors.primary700,
            () => context.push('/registro')),
        const SizedBox(height: 10),
        _dashCard(Icons.notifications_outlined, 'Notificaciones',
            'Enviar reportes por WhatsApp o email', const Color(0xFFEA580C),
            () => context.push('/notificaciones')),
      ]),
    );
  }

  Widget _buildMatriculasTab() {
    return Scaffold(
      appBar: AppBar(title: const Text('Matrículas')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        _dashCard(Icons.add_circle_outline, 'Nueva Matrícula',
            'Formulario de inscripción pública', AppColors.success,
            () => context.push('/matriculas/nueva')),
        const SizedBox(height: 12),
        _dashCard(Icons.search, 'Seguimiento',
            'Consultar estado de solicitud', AppColors.primary,
            () => context.push('/matriculas/seguimiento')),
        const SizedBox(height: 12),
        _dashCard(Icons.admin_panel_settings_outlined, 'Panel Secretaría',
            'Gestionar y aprobar solicitudes', AppColors.primary700,
            () => context.push('/matriculas/secretaria')),
      ]),
    );
  }

  Widget _buildAgentTab() {
    return Scaffold(
      appBar: AppBar(title: const Text('Agente IA')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        _dashCard(Icons.notifications_active_outlined, 'Panel de Alertas',
            'Estudiantes con bajo rendimiento o inasistencia',
            const Color(0xFFEA580C),
            () => context.push('/agente/alertas')),
        const SizedBox(height: 12),
        _dashCard(Icons.edit_note, 'Asistente de Informes',
            'Mejora la redacción de tus informes de clase',
            AppColors.primary600,
            () => context.push('/agente/informes')),
      ]),
    );
  }

  Widget _dashCard(IconData icon, String title, String subtitle, Color color, VoidCallback onTap) {
    return Card(
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
        onTap: onTap,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final role = auth.userRole ?? 'ESTUDIANTE';
    final items = _navItems(role);

    return Scaffold(
      body: _buildPage(role, _selectedIndex),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (i) => setState(() => _selectedIndex = i),
        destinations: items.map((n) => NavigationDestination(
          icon: Icon(n.icon),
          selectedIcon: Icon(n.activeIcon),
          label: n.label,
        )).toList(),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  _NavItem(this.icon, this.activeIcon, this.label);
}
