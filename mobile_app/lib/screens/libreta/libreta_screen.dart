import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../core/constants.dart';
import '../../api/api_service.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common_widgets.dart';

class LibretaScreen extends StatefulWidget {
  final int studentId;
  final String studentName;
  const LibretaScreen({super.key, required this.studentId, required this.studentName});

  @override
  State<LibretaScreen> createState() => _LibretaScreenState();
}

class _LibretaScreenState extends State<LibretaScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = ''; });
    try {
      final api = context.read<ApiService>();
      final auth = context.read<AuthProvider>();
      final data = await api.fetchLibreta(widget.studentId, authToken: auth.token);
      setState(() { _data = data; _loading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Libreta — ${widget.studentName}')),
      body: _loading
          ? const LoadingWidget(message: 'Cargando libreta...')
          : _error.isNotEmpty
              ? ErrorDisplay(message: _error, onRetry: _load)
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final d = _data!;
    final promedio = (d['promedio_general'] as num?)?.toDouble();
    final asistencia = d['asistencia'] as Map<String, dynamic>? ?? {};
    final materias = d['materias'] as Map<String, dynamic>? ?? {};

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Header card
        Card(
          color: AppColors.primary,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(children: [
              const CircleAvatar(
                radius: 28,
                backgroundColor: Colors.white24,
                child: Icon(Icons.person, color: Colors.white, size: 32),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(d['nombre']?.toString() ?? '',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 4),
                  if (promedio != null)
                    Text('Promedio general: ${promedio.toStringAsFixed(2)}',
                        style: const TextStyle(color: Colors.white70, fontSize: 13)),
                ]),
              ),
              if (promedio != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _promedioColor(promedio).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.white30),
                  ),
                  child: Column(children: [
                    Text(promedio.toStringAsFixed(1),
                        style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                    Text(GradeLabels.nivel(promedio),
                        style: const TextStyle(color: Colors.white70, fontSize: 10)),
                  ]),
                ),
            ]),
          ),
        ),

        const SizedBox(height: 16),

        // Asistencia summary
        const SectionHeader(title: 'Asistencia'),
        Row(children: [
          Expanded(child: StatCard(
            label: 'Total', value: '${asistencia['total'] ?? 0}',
            icon: Icons.event_note, color: AppColors.primary,
          )),
          const SizedBox(width: 8),
          Expanded(child: StatCard(
            label: 'Presentes', value: '${asistencia['presentes'] ?? 0}',
            icon: Icons.check_circle, color: AppColors.success,
          )),
          const SizedBox(width: 8),
          Expanded(child: StatCard(
            label: 'Ausentes', value: '${asistencia['ausentes'] ?? 0}',
            icon: Icons.cancel, color: AppColors.error,
          )),
        ]),
        if ((asistencia['porcentaje'] as num?) != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: LinearProgressIndicator(
              value: (asistencia['porcentaje'] as num).toDouble() / 100,
              backgroundColor: AppColors.error.withOpacity(0.15),
              valueColor: const AlwaysStoppedAnimation<Color>(AppColors.success),
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            '${(asistencia['porcentaje'] as num?)?.toStringAsFixed(1) ?? 0}% de asistencia',
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
        ),

        const SizedBox(height: 20),

        // Calificaciones por materia
        const SectionHeader(title: 'Calificaciones por materia'),
        if (materias.isEmpty)
          const EmptyState(message: 'Sin calificaciones registradas', icon: Icons.grade_outlined)
        else
          ...materias.entries.map((entry) => _MateriaCard(
                materia: entry.key,
                notas: entry.value as List<dynamic>,
              )),
      ]),
    );
  }

  Color _promedioColor(double p) {
    if (p >= 9) return AppColors.dar;
    if (p >= 7) return AppColors.aar;
    if (p > 4) return AppColors.paar;
    return AppColors.naar;
  }
}

class _MateriaCard extends StatelessWidget {
  final String materia;
  final List<dynamic> notas;

  const _MateriaCard({required this.materia, required this.notas});

  double? get _promedio {
    final vals = notas
        .map((n) => (n['calificacion'] as num?)?.toDouble())
        .whereType<double>()
        .toList();
    if (vals.isEmpty) return null;
    return vals.reduce((a, b) => a + b) / vals.length;
  }

  @override
  Widget build(BuildContext context) {
    final prom = _promedio;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ExpansionTile(
        leading: Container(
          width: 40, height: 40,
          decoration: BoxDecoration(
            color: _color(prom).withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Center(child: GradeBadge(nota: prom)),
        ),
        title: Text(materia, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text('${notas.length} registros · prom. ${prom?.toStringAsFixed(1) ?? '—'}',
            style: const TextStyle(fontSize: 11)),
        children: notas.map((n) => ListTile(
          dense: true,
          title: Text(
            '${n['parcial'] ?? ''} ${n['quimestre'] ?? ''} — ${n['tipo_aporte'] ?? ''}',
            style: const TextStyle(fontSize: 13),
          ),
          trailing: GradeBadge(nota: (n['calificacion'] as num?)?.toDouble()),
        )).toList(),
      ),
    );
  }

  Color _color(double? p) {
    if (p == null) return AppColors.textMuted;
    if (p >= 9) return AppColors.dar;
    if (p >= 7) return AppColors.aar;
    if (p > 4) return AppColors.paar;
    return AppColors.naar;
  }
}
