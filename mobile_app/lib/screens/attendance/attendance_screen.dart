import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/attendance_provider.dart';
import '../../widgets/common_widgets.dart';

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  void _load() {
    final auth = context.read<AuthProvider>();
    final id = auth.studentId;
    if (id != null) context.read<AttendanceProvider>().fetchAttendance(id);
  }

  @override
  Widget build(BuildContext context) {
    final attend = context.watch<AttendanceProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Asistencia')),
      body: Column(children: [
        // Resumen
        Container(
          color: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(children: [
            Expanded(child: _stat('Total', attend.totalClases.toString(), AppColors.primary)),
            Expanded(child: _stat('Presentes', attend.presentes.toString(), AppColors.success)),
            Expanded(child: _stat('Ausentes', attend.ausentes.toString(), AppColors.error)),
            Expanded(child: _stat('Tardanzas', attend.tardanzas.toString(), AppColors.warning)),
          ]),
        ),
        const Divider(height: 1),

        // Lista
        Expanded(
          child: attend.isLoading
              ? const LoadingWidget(message: 'Cargando asistencia...')
              : attend.errorMessage.isNotEmpty
                  ? ErrorDisplay(message: attend.errorMessage, onRetry: _load)
                  : attend.records.isEmpty
                      ? const EmptyState(message: 'Sin registros de asistencia', icon: Icons.event_note_outlined)
                      : ListView.builder(
                          padding: const EdgeInsets.all(8),
                          itemCount: attend.records.length,
                          itemBuilder: (ctx, i) => _buildRow(attend.records[i]),
                        ),
        ),
      ]),
    );
  }

  Widget _stat(String label, String val, Color color) {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Text(val, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
      Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
    ]);
  }

  Widget _buildRow(dynamic record) {
    final estado = record['estado']?.toString() ?? '';
    Color color;
    IconData icon;
    switch (estado.toLowerCase()) {
      case 'presente': color = AppColors.success; icon = Icons.check_circle; break;
      case 'ausente': color = AppColors.error; icon = Icons.cancel; break;
      case 'tardanza': color = AppColors.warning; icon = Icons.schedule; break;
      default: color = AppColors.textMuted; icon = Icons.help_outline;
    }

    String fecha = record['fecha']?.toString() ?? '';
    try {
      final dt = DateTime.parse(fecha);
      fecha = DateFormat('dd/MM/yyyy').format(dt);
    } catch (_) {}

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.1),
          child: Icon(icon, color: color, size: 20),
        ),
        title: Text(fecha, style: const TextStyle(fontSize: 14)),
        subtitle: Text(record['observacion']?.toString() ?? '', style: const TextStyle(fontSize: 11)),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(6),
          ),
          child: Text(estado, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold)),
        ),
      ),
    );
  }
}
