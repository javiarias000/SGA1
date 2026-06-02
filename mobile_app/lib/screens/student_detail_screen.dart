import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../core/theme.dart';
import '../providers/auth_provider.dart';
import '../providers/student_provider.dart';
import '../models/student.dart';
import 'student_form_screen.dart';

class StudentDetailScreen extends StatefulWidget {
  final int studentId;
  const StudentDetailScreen({super.key, required this.studentId});

  @override
  State<StudentDetailScreen> createState() => _StudentDetailScreenState();
}

class _StudentDetailScreenState extends State<StudentDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<StudentProvider>().fetchStudentDetail(widget.studentId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final prov = context.watch<StudentProvider>();
    final auth = context.watch<AuthProvider>();
    final isDocente = auth.userRole == 'DOCENTE' || auth.isStaff;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle Estudiante'),
        actions: [
          if (prov.selectedStudent != null && isDocente)
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => StudentFormScreen(student: prov.selectedStudent))),
            ),
          if (prov.selectedStudent != null && isDocente)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: () => _confirmDelete(prov),
            ),
        ],
      ),
      body: prov.isLoading
          ? const Center(child: CircularProgressIndicator())
          : prov.errorMessage.isNotEmpty
              ? Center(child: Text(prov.errorMessage, style: const TextStyle(color: Colors.red)))
              : prov.selectedStudent == null
                  ? const Center(child: Text('Estudiante no encontrado.'))
                  : _buildDetail(prov.selectedStudent!, isDocente),
    );
  }

  Widget _buildDetail(Student s, bool isDocente) {
    final nombre = s.name ?? s.usuario?.nombre ?? 'Sin nombre';
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Header card
        Card(
          color: AppColors.primary,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(children: [
              CircleAvatar(
                radius: 28, backgroundColor: Colors.white24,
                child: Text(nombre[0].toUpperCase(),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 22)),
              ),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(nombre, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
                if (s.gradeLevelName != null)
                  Text(s.gradeLevelName!, style: const TextStyle(color: Colors.white70, fontSize: 13)),
              ])),
            ]),
          ),
        ),

        const SizedBox(height: 16),

        _section('Datos personales', [
          _row(Icons.email, 'Email', s.usuario?.email ?? '—'),
          _row(Icons.phone, 'Teléfono', s.usuario?.phone ?? '—'),
          _row(Icons.badge, 'Cédula', s.usuario?.cedula ?? '—'),
        ]),

        _section('Representante', [
          _row(Icons.person, 'Nombre', s.parentName ?? '—'),
          _row(Icons.email_outlined, 'Email', s.parentEmail ?? '—'),
          _row(Icons.phone_outlined, 'Teléfono', s.parentPhone ?? '—'),
        ]),

        _section('Académico', [
          _row(Icons.school, 'Docente', s.teacherFullName ?? '—'),
          _row(Icons.grade, 'Código', s.registrationCode ?? '—'),
        ]),

        const SizedBox(height: 16),
        if (isDocente) ...[
          const Divider(),
          const Text('Acciones rápidas',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.textMuted)),
          const SizedBox(height: 12),
          _actionBtn(Icons.grade, 'Ingresar Calificación', AppColors.aar, () {
            context.push('/grades/entry/${s.id}?name=${Uri.encodeComponent(nombre)}');
          }),
          const SizedBox(height: 8),
          _actionBtn(Icons.book, 'Ver Libreta', AppColors.primary, () {
            context.push('/libreta/${s.id}?name=${Uri.encodeComponent(nombre)}');
          }),
          const SizedBox(height: 8),
          _actionBtn(Icons.smart_toy_outlined, 'Analizar con IA', AppColors.warning, () async {
            // trigger análisis IA
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Iniciando análisis IA...')),
            );
          }),
        ],
      ]),
    );
  }

  Widget _section(String title, List<Widget> rows) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textMuted)),
      ),
      Card(
        child: Column(children: rows),
      ),
      const SizedBox(height: 8),
    ]);
  }

  Widget _row(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(children: [
        Icon(icon, size: 18, color: AppColors.primary),
        const SizedBox(width: 10),
        Text('$label: ', style: const TextStyle(fontSize: 13, color: AppColors.textMuted)),
        Expanded(
          child: Text(value,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
              overflow: TextOverflow.ellipsis),
        ),
      ]),
    );
  }

  Widget _actionBtn(IconData icon, String label, Color color, VoidCallback onTap) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, color: color, size: 18),
        label: Text(label, style: TextStyle(color: color)),
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: color.withOpacity(0.4)),
          padding: const EdgeInsets.symmetric(vertical: 12),
        ),
      ),
    );
  }

  void _confirmDelete(StudentProvider prov) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Eliminar estudiante'),
        content: const Text('¿Seguro que deseas eliminar este estudiante?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          ElevatedButton(
            onPressed: () async {
              await prov.deleteStudent(prov.selectedStudent!.id);
              if (mounted) {
                Navigator.pop(context);
                Navigator.pop(context);
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
  }
}
