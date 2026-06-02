import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/grade_provider.dart';
import '../../providers/tipo_aporte_provider.dart';
import '../../providers/clase_provider.dart';

class GradeEntryScreen extends StatefulWidget {
  final int studentId;
  final String studentName;
  const GradeEntryScreen({super.key, required this.studentId, required this.studentName});

  @override
  State<GradeEntryScreen> createState() => _GradeEntryScreenState();
}

class _GradeEntryScreenState extends State<GradeEntryScreen> {
  final _notaCtrl = TextEditingController();
  int? _subjectId;
  String _parcial = '1P';
  String _quimestre = 'Q1';
  int? _tipoAporteId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TipoAporteProvider>().fetchTiposAporte();
      context.read<ClaseProvider>().fetchClases();
    });
  }

  @override
  void dispose() {
    _notaCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final nota = double.tryParse(_notaCtrl.text);
    if (nota == null || nota < 0 || nota > 10) {
      _snack('Ingresa una nota válida (0–10).');
      return;
    }
    if (_subjectId == null) {
      _snack('Selecciona una materia.');
      return;
    }
    if (_tipoAporteId == null) {
      _snack('Selecciona el tipo de aporte.');
      return;
    }
    setState(() => _saving = true);
    try {
      await context.read<GradeProvider>().saveGrade(
        studentId: widget.studentId,
        subjectId: _subjectId!,
        parcial: _parcial,
        quimestre: _quimestre,
        tipoAporteId: _tipoAporteId!,
        calificacion: nota,
      );
      if (mounted) {
        _snack('Calificación guardada correctamente.');
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) _snack('Error: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    final tiposAporte = context.watch<TipoAporteProvider>();
    final clases = context.watch<ClaseProvider>();

    // Build subject list from clases
    final subjects = <Map<String, dynamic>>[];
    for (final c in clases.clases) {
      final subj = c.subject;
      if (subj != null) {
        final id = subj.id;
        final name = subj.name;
        if (!subjects.any((s) => s['id'] == id)) {
          subjects.add({'id': id, 'name': name});
        }
      }
    }

    return Scaffold(
      appBar: AppBar(title: Text('Calificación — ${widget.studentName}')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(children: [
          // Subject dropdown
          if (clases.isLoading)
            const LinearProgressIndicator()
          else
            DropdownButtonFormField<int>(
              value: _subjectId,
              decoration: const InputDecoration(
                labelText: 'Materia',
                prefixIcon: Icon(Icons.subject),
                border: OutlineInputBorder(),
              ),
              items: subjects
                  .map((s) => DropdownMenuItem<int>(
                      value: s['id'] as int, child: Text(s['name'].toString())))
                  .toList(),
              onChanged: (v) => setState(() => _subjectId = v),
              hint: const Text('Selecciona materia'),
            ),

          const SizedBox(height: 16),
          Row(children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _parcial,
                decoration: const InputDecoration(
                  labelText: 'Parcial', border: OutlineInputBorder(),
                ),
                items: ['1P', '2P', '3P', '4P']
                    .map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
                onChanged: (v) => setState(() => _parcial = v ?? '1P'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _quimestre,
                decoration: const InputDecoration(
                  labelText: 'Quimestre', border: OutlineInputBorder(),
                ),
                items: ['Q1', 'Q2']
                    .map((q) => DropdownMenuItem(value: q, child: Text(q))).toList(),
                onChanged: (v) => setState(() => _quimestre = v ?? 'Q1'),
              ),
            ),
          ]),

          const SizedBox(height: 16),
          if (tiposAporte.isLoading)
            const LinearProgressIndicator()
          else
            DropdownButtonFormField<int>(
              value: _tipoAporteId,
              decoration: const InputDecoration(
                labelText: 'Tipo de Aporte',
                prefixIcon: Icon(Icons.category),
                border: OutlineInputBorder(),
              ),
              items: tiposAporte.tiposAporte
                  .map((t) => DropdownMenuItem<int>(value: t.id, child: Text(t.nombre)))
                  .toList(),
              onChanged: (v) => setState(() => _tipoAporteId = v),
              hint: const Text('Selecciona tipo de aporte'),
            ),

          const SizedBox(height: 16),
          TextField(
            controller: _notaCtrl,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Nota (0 – 10)',
              prefixIcon: Icon(Icons.grade),
              border: OutlineInputBorder(),
            ),
          ),

          const SizedBox(height: 28),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: _saving
                ? const Center(child: CircularProgressIndicator())
                : ElevatedButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text('Guardar calificación'),
                  ),
          ),
        ]),
      ),
    );
  }
}
