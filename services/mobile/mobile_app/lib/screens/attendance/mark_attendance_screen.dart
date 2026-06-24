import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../core/theme.dart';
import '../../models/student.dart';
import '../../providers/auth_provider.dart';
import '../../providers/student_provider.dart';
import '../../api/api_service.dart';
import '../../widgets/common_widgets.dart';

class MarkAttendanceScreen extends StatefulWidget {
  const MarkAttendanceScreen({super.key});

  @override
  State<MarkAttendanceScreen> createState() => _MarkAttendanceScreenState();
}

class _MarkAttendanceScreenState extends State<MarkAttendanceScreen> {
  DateTime _selectedDate = DateTime.now();
  final Map<int, String> _estados = {};
  final Map<int, int?> _inscripcionIds = {};
  bool _saving = false;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<StudentProvider>().fetchStudents();
    });
  }

  Future<void> _selectDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2024),
      lastDate: DateTime.now(),
    );
    if (picked != null) setState(() => _selectedDate = picked);
  }

  Future<void> _guardar() async {
    if (_estados.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Marca al menos una asistencia.')),
      );
      return;
    }

    setState(() { _saving = true; _saved = false; });
    final api = context.read<ApiService>();
    final auth = context.read<AuthProvider>();
    final fecha = DateFormat('yyyy-MM-dd').format(_selectedDate);
    int errors = 0;

    for (final entry in _estados.entries) {
      final inscripcionId = _inscripcionIds[entry.key];
      if (inscripcionId == null) continue;
      try {
        await api.markAttendance({
          'inscripcion': inscripcionId,
          'fecha': fecha,
          'estado': entry.value,
        }, authToken: auth.token);
      } catch (_) {
        errors++;
      }
    }

    setState(() { _saving = false; _saved = errors == 0; });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(errors == 0
            ? 'Asistencia guardada correctamente.'
            : 'Se guardaron con $errors errores.'),
        backgroundColor: errors == 0 ? AppColors.success : AppColors.error,
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final students = context.watch<StudentProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Registrar Asistencia'),
        actions: [
          TextButton.icon(
            onPressed: _saving ? null : _guardar,
            icon: _saving
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.save, color: Colors.white),
            label: const Text('Guardar', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
      body: Column(children: [
        // Date picker
        InkWell(
          onTap: _selectDate,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Colors.white,
            child: Row(children: [
              const Icon(Icons.calendar_today, color: AppColors.primary),
              const SizedBox(width: 12),
              Text(
                DateFormat('EEEE, dd MMMM yyyy', 'es').format(_selectedDate),
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              ),
              const Spacer(),
              const Icon(Icons.edit, size: 16, color: AppColors.textMuted),
            ]),
          ),
        ),
        const Divider(height: 1),

        // Legend
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(children: [
            _legend(AppColors.success, 'Presente'),
            const SizedBox(width: 16),
            _legend(AppColors.error, 'Ausente'),
            const SizedBox(width: 16),
            _legend(AppColors.warning, 'Justificado'),
          ]),
        ),
        const Divider(height: 1),

        // Students list
        Expanded(
          child: students.isLoading
              ? const LoadingWidget(message: 'Cargando estudiantes...')
              : students.students.isEmpty
                  ? const EmptyState(message: 'Sin estudiantes', icon: Icons.people_outline)
                  : ListView.builder(
                      itemCount: students.students.length,
                      itemBuilder: (ctx, i) {
                        final s = students.students[i];
                        final estado = _estados[s.id] ?? '';
                        return _StudentAttendanceRow(
                          student: s,
                          estado: estado,
                          onEstadoChanged: (v) => setState(() => _estados[s.id] = v),
                        );
                      },
                    ),
        ),
      ]),
    );
  }

  Widget _legend(Color color, String label) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 4),
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
        ],
      );
}

class _StudentAttendanceRow extends StatelessWidget {
  final Student student;
  final String estado;
  final ValueChanged<String> onEstadoChanged;

  const _StudentAttendanceRow({
    required this.student,
    required this.estado,
    required this.onEstadoChanged,
  });

  @override
  Widget build(BuildContext context) {
    final name = student.name ?? student.usuario?.nombre ?? 'Estudiante';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: Color(0xFFE5E7EB))),
      ),
      child: Row(children: [
        CircleAvatar(
          radius: 18,
          backgroundColor: AppColors.primary.withOpacity(0.1),
          child: Text(
            name.isNotEmpty ? name[0].toUpperCase() : '?',
            style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
        ),
        _btn('P', 'Presente', AppColors.success, estado == 'Presente'),
        const SizedBox(width: 6),
        _btn('A', 'Ausente', AppColors.error, estado == 'Ausente'),
        const SizedBox(width: 6),
        _btn('J', 'Justificado', AppColors.warning, estado == 'Justificado'),
      ]),
    );
  }

  Widget _btn(String label, String value, Color color, bool selected) {
    return GestureDetector(
      onTap: () => onEstadoChanged(value),
      child: Container(
        width: 32, height: 32,
        decoration: BoxDecoration(
          color: selected ? color : color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.4)),
        ),
        child: Center(
          child: Text(label,
              style: TextStyle(
                  color: selected ? Colors.white : color,
                  fontWeight: FontWeight.bold,
                  fontSize: 13)),
        ),
      ),
    );
  }
}
