import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/grade_provider.dart';
import '../../widgets/common_widgets.dart';

class GradesScreen extends StatefulWidget {
  const GradesScreen({super.key});

  @override
  State<GradesScreen> createState() => _GradesScreenState();
}

class _GradesScreenState extends State<GradesScreen> {
  String _parcial = '';
  String _quimestre = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  void _load() {
    final auth = context.read<AuthProvider>();
    final id = auth.studentId;
    if (id != null) {
      context.read<GradeProvider>().fetchGrades(id,
          parcial: _parcial.isEmpty ? null : _parcial,
          quimestre: _quimestre.isEmpty ? null : _quimestre);
    }
  }

  @override
  Widget build(BuildContext context) {
    final grades = context.watch<GradeProvider>();
    final auth = context.watch<AuthProvider>();
    final isDocente = auth.userRole == 'DOCENTE' || auth.isStaff;

    return Scaffold(
      appBar: AppBar(title: const Text('Calificaciones')),
      body: Column(
        children: [
          // Filtros
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(children: [
              Expanded(child: _dropdown('Parcial', _parcial, ['', '1P', '2P', '3P', '4P'],
                  (v) => setState(() { _parcial = v ?? ''; _load(); }))),
              const SizedBox(width: 12),
              Expanded(child: _dropdown('Quimestre', _quimestre, ['', 'Q1', 'Q2'],
                  (v) => setState(() { _quimestre = v ?? ''; _load(); }))),
            ]),
          ),
          const Divider(height: 1),

          Expanded(
            child: grades.isLoading
                ? const LoadingWidget(message: 'Cargando calificaciones...')
                : grades.errorMessage.isNotEmpty
                    ? ErrorDisplay(message: grades.errorMessage, onRetry: _load)
                    : grades.gradesList.isEmpty
                        ? const EmptyState(message: 'Sin calificaciones registradas', icon: Icons.grade_outlined)
                        : _buildList(grades.gradesList, isDocente),
          ),
        ],
      ),
    );
  }

  Widget _buildList(List<dynamic> list, bool isDocente) {
    // Agrupar por materia
    final Map<String, List<dynamic>> byMateria = {};
    for (final g in list) {
      final mat = g['subject']?.toString() ?? g['materia']?.toString() ?? 'Sin materia';
      byMateria.putIfAbsent(mat, () => []).add(g);
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: byMateria.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, i) {
        final materia = byMateria.keys.elementAt(i);
        final notas = byMateria[materia]!;
        final promedio = _calcPromedio(notas);

        return Card(
          child: ExpansionTile(
            leading: Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: _colorNota(promedio).withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(child: GradeBadge(nota: promedio)),
            ),
            title: Text(materia, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text('${notas.length} registros', style: const TextStyle(fontSize: 11)),
            children: notas.map((g) => _gradeRow(g)).toList(),
          ),
        );
      },
    );
  }

  Widget _gradeRow(dynamic g) {
    final nota = _parseNota(g['calificacion'] ?? g['nota']);
    final parcial = g['parcial']?.toString() ?? '';
    final tipo = g['tipo_aporte']?.toString() ?? g['descripcion']?.toString() ?? '';
    final quim = g['quimestre']?.toString() ?? '';

    return ListTile(
      dense: true,
      title: Text('$parcial $quim — $tipo',
          style: const TextStyle(fontSize: 13)),
      trailing: GradeBadge(nota: nota),
    );
  }

  Widget _dropdown(String hint, String value, List<String> options, ValueChanged<String?> onChanged) {
    return DropdownButtonFormField<String>(
      value: value,
      decoration: InputDecoration(
        labelText: hint,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
      ),
      items: options.map((o) => DropdownMenuItem(value: o, child: Text(o.isEmpty ? 'Todos' : o))).toList(),
      onChanged: onChanged,
    );
  }

  double? _parseNota(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  double? _calcPromedio(List<dynamic> notas) {
    final vals = notas.map((g) => _parseNota(g['calificacion'] ?? g['nota'])).whereType<double>().toList();
    if (vals.isEmpty) return null;
    return vals.reduce((a, b) => a + b) / vals.length;
  }

  Color _colorNota(double? nota) {
    if (nota == null) return AppColors.textMuted;
    if (nota >= 9) return AppColors.dar;
    if (nota >= 7) return AppColors.aar;
    if (nota > 4) return AppColors.paar;
    return AppColors.naar;
  }
}
