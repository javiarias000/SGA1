import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../core/theme.dart';
import '../../models/student.dart';
import '../../providers/auth_provider.dart';
import '../../providers/activity_provider.dart';
import '../../providers/student_provider.dart';
import '../../providers/clase_provider.dart';
import '../../models/activity.dart';
import '../../widgets/common_widgets.dart';

class RegistroScreen extends StatefulWidget {
  const RegistroScreen({super.key});

  @override
  State<RegistroScreen> createState() => _RegistroScreenState();
}

class _RegistroScreenState extends State<RegistroScreen> {
  int? _studentFilter;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ActivityProvider>().fetchActividades();
      context.read<StudentProvider>().fetchStudents();
    });
  }

  void _load() {
    context.read<ActivityProvider>().fetchActividades(studentId: _studentFilter);
  }

  @override
  Widget build(BuildContext context) {
    final prov = context.watch<ActivityProvider>();
    final students = context.watch<StudentProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Registro de Clases'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _showFormDialog(context),
          ),
        ],
      ),
      body: Column(children: [
        // Student filter
        if (!students.isLoading && students.students.isNotEmpty)
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: DropdownButtonFormField<int?>(
              value: _studentFilter,
              decoration: const InputDecoration(
                labelText: 'Filtrar por estudiante',
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem<int?>(value: null, child: Text('Todos')),
                ...students.students.map((s) => DropdownMenuItem<int?>(
                    value: s.id,
                    child: Text(s.name ?? s.usuario?.nombre ?? 'Estudiante ${s.id}'))),
              ],
              onChanged: (v) => setState(() { _studentFilter = v; _load(); }),
            ),
          ),

        Expanded(
          child: prov.isLoading
              ? const LoadingWidget(message: 'Cargando actividades...')
              : prov.errorMessage.isNotEmpty
                  ? ErrorDisplay(message: prov.errorMessage, onRetry: _load)
                  : prov.activities.isEmpty
                      ? const EmptyState(
                          message: 'Sin actividades registradas', icon: Icons.event_note_outlined)
                      : ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: prov.activities.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (ctx, i) => _ActivityCard(
                            activity: prov.activities[i],
                            onDelete: () => _delete(prov.activities[i].id),
                          ),
                        ),
        ),
      ]),
    );
  }

  Future<void> _delete(int id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Eliminar actividad'),
        content: const Text('¿Eliminar este registro de clase?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (ok == true && mounted) {
      await context.read<ActivityProvider>().deleteActividad(id);
    }
  }

  void _showFormDialog(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => _ActivityForm(onSaved: _load),
    );
  }
}

class _ActivityCard extends StatelessWidget {
  final Activity activity;
  final VoidCallback onDelete;

  const _ActivityCard({required this.activity, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final perfColors = {
      'Excelente': AppColors.dar,
      'Muy Bueno': AppColors.aar,
      'Bueno': AppColors.success,
      'Regular': AppColors.warning,
      'Necesita mejorar': AppColors.error,
    };
    final color = perfColors[activity.performance] ?? AppColors.textMuted;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(6),
              ),
              child: Text('Clase #${activity.classNumber}',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(width: 8),
            Text(
              DateFormat('dd/MM/yyyy').format(activity.date),
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(6),
              ),
              child: Text(activity.performance,
                  style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold)),
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline, size: 18, color: AppColors.textMuted),
              onPressed: onDelete,
            ),
          ]),
          if (activity.subjectNombre.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(activity.subjectNombre,
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            ),
          if (activity.topicsWorked.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Temas: ${activity.topicsWorked}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
            ),
          if (activity.homework.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(children: [
                const Icon(Icons.home_work_outlined, size: 13, color: AppColors.warning),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(activity.homework,
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                ),
              ]),
            ),
        ]),
      ),
    );
  }
}

class _ActivityForm extends StatefulWidget {
  final VoidCallback onSaved;
  const _ActivityForm({required this.onSaved});

  @override
  State<_ActivityForm> createState() => _ActivityFormState();
}

class _ActivityFormState extends State<_ActivityForm> {
  final _topicsCtrl = TextEditingController();
  final _piecesCtrl = TextEditingController();
  final _homeworkCtrl = TextEditingController();
  final _obsCtrl = TextEditingController();
  String _performance = 'Bueno';
  int _practiceTime = 30;
  int? _studentId;
  int? _claseId;
  DateTime _date = DateTime.now();
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ClaseProvider>().fetchClases();
    });
  }

  @override
  void dispose() {
    _topicsCtrl.dispose();
    _piecesCtrl.dispose();
    _homeworkCtrl.dispose();
    _obsCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_studentId == null || _claseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona estudiante y clase.')),
      );
      return;
    }
    setState(() => _saving = true);
    final ok = await context.read<ActivityProvider>().createActividad({
      'student': _studentId,
      'clase': _claseId,
      'date': DateFormat('yyyy-MM-dd').format(_date),
      'topics_worked': _topicsCtrl.text.trim(),
      'pieces': _piecesCtrl.text.trim(),
      'performance': _performance,
      'homework': _homeworkCtrl.text.trim(),
      'practice_time': _practiceTime,
      'observations': _obsCtrl.text.trim(),
    });
    setState(() => _saving = false);
    if (mounted) {
      Navigator.pop(context);
      if (ok) widget.onSaved();
    }
  }

  @override
  Widget build(BuildContext context) {
    final students = context.watch<StudentProvider>();
    final clases = context.watch<ClaseProvider>();

    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text('Nueva Actividad', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 16),
          DropdownButtonFormField<int>(
            value: _studentId,
            decoration: const InputDecoration(labelText: 'Estudiante *', border: OutlineInputBorder()),
            hint: const Text('Selecciona'),
            items: students.students.map((s) => DropdownMenuItem<int>(
                value: s.id,
                child: Text(s.name ?? s.usuario?.nombre ?? 'Estudiante ${s.id}'))).toList(),
            onChanged: (v) => setState(() => _studentId = v),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            value: _claseId,
            decoration: const InputDecoration(labelText: 'Clase *', border: OutlineInputBorder()),
            hint: const Text('Selecciona'),
            items: clases.clases.map((c) {
              final name = c.subject?.name ?? c.name;
              return DropdownMenuItem<int>(value: c.id, child: Text(name));
            }).toList(),
            onChanged: (v) => setState(() => _claseId = v),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _performance,
            decoration: const InputDecoration(labelText: 'Desempeño', border: OutlineInputBorder()),
            items: ['Excelente', 'Muy Bueno', 'Bueno', 'Regular', 'Necesita mejorar']
                .map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
            onChanged: (v) => setState(() => _performance = v ?? 'Bueno'),
          ),
          const SizedBox(height: 12),
          TextField(controller: _topicsCtrl, decoration: const InputDecoration(labelText: 'Temas trabajados', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _piecesCtrl, decoration: const InputDecoration(labelText: 'Piezas / Repertorio', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _homeworkCtrl, decoration: const InputDecoration(labelText: 'Tarea para casa', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _obsCtrl, maxLines: 2, decoration: const InputDecoration(labelText: 'Observaciones', border: OutlineInputBorder(), alignLabelWithHint: true)),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity, height: 48,
            child: _saving
                ? const Center(child: CircularProgressIndicator())
                : ElevatedButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text('Registrar Clase'),
                  ),
          ),
        ]),
      ),
    );
  }
}
