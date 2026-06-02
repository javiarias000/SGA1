import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../models/student.dart';
import '../../providers/auth_provider.dart';
import '../../providers/student_provider.dart';
import '../../widgets/common_widgets.dart';

class NotificacionesScreen extends StatefulWidget {
  const NotificacionesScreen({super.key});

  @override
  State<NotificacionesScreen> createState() => _NotificacionesScreenState();
}

class _NotificacionesScreenState extends State<NotificacionesScreen> {
  int? _selectedStudentId;
  String? _selectedStudentName;
  final Map<String, bool> _sending = {};
  final Map<String, bool> _sent = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<StudentProvider>().fetchStudents();
    });
  }

  Future<void> _enviar(String tipo) async {
    if (_selectedStudentId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona un estudiante primero.')),
      );
      return;
    }
    setState(() => _sending[tipo] = true);
    try {
      final api = context.read<ApiService>();
      final auth = context.read<AuthProvider>();
      if (tipo == 'email') {
        await api.enviarReporteEmail(
            studentId: _selectedStudentId!, authToken: auth.token);
      } else {
        await api.enviarNotificacionWhatsApp(
            studentId: _selectedStudentId!, tipo: tipo, authToken: auth.token);
      }
      setState(() => _sent[tipo] = true);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Notificación enviada a $_selectedStudentName'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _sending[tipo] = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final students = context.watch<StudentProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Notificaciones')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Student selector
          const Text('Estudiante',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(height: 8),
          students.isLoading
              ? const LinearProgressIndicator()
              : DropdownButtonFormField<int>(
                  value: _selectedStudentId,
                  decoration: const InputDecoration(
                    hintText: 'Selecciona un estudiante',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.person_search),
                  ),
                  items: students.students
                      .map((s) => DropdownMenuItem<int>(
                            value: s.id,
                            child: Text(s.name ?? s.usuario?.nombre ?? 'Estudiante ${s.id}'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() {
                    _selectedStudentId = v;
                    _sent.clear();
                    final found = students.students
                        .firstWhere((s) => s.id == v,
                            orElse: () => students.students.first);
                    _selectedStudentName = found.name ?? found.usuario?.nombre;
                  }),
                ),

          const SizedBox(height: 24),
          const Text('WhatsApp',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(height: 8),

          _NotifCard(
            icon: Icons.grade,
            color: AppColors.aar,
            title: 'Reporte de Calificaciones',
            subtitle: 'Envía notas actuales al representante',
            isSending: _sending['grades'] == true,
            isSent: _sent['grades'] == true,
            onTap: () => _enviar('grades'),
          ),
          const SizedBox(height: 10),
          _NotifCard(
            icon: Icons.event_note,
            color: AppColors.primary,
            title: 'Reporte de Asistencia',
            subtitle: 'Envía historial de asistencia',
            isSending: _sending['attendance'] == true,
            isSent: _sent['attendance'] == true,
            onTap: () => _enviar('attendance'),
          ),

          const SizedBox(height: 24),
          const Text('Email',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(height: 8),

          _NotifCard(
            icon: Icons.email_outlined,
            color: const Color(0xFFEA580C),
            title: 'Informe por Correo',
            subtitle: 'Envía informe académico completo al email del representante',
            isSending: _sending['email'] == true,
            isSent: _sent['email'] == true,
            onTap: () => _enviar('email'),
          ),
        ]),
      ),
    );
  }
}

class _NotifCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final bool isSending;
  final bool isSent;
  final VoidCallback onTap;

  const _NotifCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.isSending,
    required this.isSent,
    required this.onTap,
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
          child: Icon(icon, color: color),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
        trailing: isSending
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
            : isSent
                ? const Icon(Icons.check_circle, color: AppColors.success)
                : Icon(Icons.send, color: color),
        onTap: isSending ? null : onTap,
      ),
    );
  }
}

