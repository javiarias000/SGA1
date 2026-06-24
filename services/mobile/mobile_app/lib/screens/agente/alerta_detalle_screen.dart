import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common_widgets.dart';

class AlertaDetalleScreen extends StatefulWidget {
  final int alertaId;
  const AlertaDetalleScreen({super.key, required this.alertaId});

  @override
  State<AlertaDetalleScreen> createState() => _AlertaDetalleScreenState();
}

class _AlertaDetalleScreenState extends State<AlertaDetalleScreen> {
  Map<String, dynamic>? _alerta;
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
      final data = await api.fetchAlertaDetalle(widget.alertaId, authToken: auth.authToken);
      setState(() => _alerta = data);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _cambiarEstado(String nuevoEstado) async {
    try {
      final api = context.read<ApiService>();
      final auth = context.read<AuthProvider>();
      await api.actualizarEstadoAlerta(widget.alertaId, nuevoEstado, authToken: auth.authToken);
      setState(() => _alerta!['estado'] = nuevoEstado);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Estado: $nuevoEstado')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Detalle de Alerta')),
      body: _loading
          ? const LoadingWidget()
          : _error.isNotEmpty
              ? ErrorDisplay(message: _error, onRetry: _load)
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final a = _alerta!;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        // Header
        Card(child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              SeverityChip(severidad: a['severidad']?.toString() ?? ''),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(a['estado']?.toString() ?? '',
                    style: const TextStyle(fontSize: 10, color: AppColors.primary, fontWeight: FontWeight.bold)),
              ),
            ]),
            const SizedBox(height: 10),
            Text(a['estudiante']?['nombre']?.toString() ?? '',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
            Text(a['tipo_display']?.toString() ?? '',
                style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
            if (a['materia'] != null) ...[
              const SizedBox(height: 6),
              Row(children: [
                const Icon(Icons.subject, size: 14, color: AppColors.textMuted),
                const SizedBox(width: 4),
                Text(a['materia'].toString(), style: const TextStyle(fontSize: 12)),
              ]),
            ],
            if (a['promedio_detectado'] != null) ...[
              const SizedBox(height: 4),
              Row(children: [
                const Icon(Icons.bar_chart, size: 14, color: AppColors.textMuted),
                const SizedBox(width: 4),
                Text('Promedio: ${a['promedio_detectado']}', style: const TextStyle(fontSize: 12)),
              ]),
            ],
            if (a['porcentaje_inasistencia'] != null) ...[
              const SizedBox(height: 4),
              Row(children: [
                const Icon(Icons.event_busy, size: 14, color: AppColors.textMuted),
                const SizedBox(width: 4),
                Text('Inasistencia: ${a['porcentaje_inasistencia']}%', style: const TextStyle(fontSize: 12)),
              ]),
            ],
          ]),
        )),

        const SizedBox(height: 12),

        // Análisis IA
        if (a['analisis_ia'] != null && a['analisis_ia'].toString().isNotEmpty)
          _section('🧠 Análisis del Agente', a['analisis_ia'].toString(), AppColors.primary),

        if (a['recomendaciones_ia'] != null && a['recomendaciones_ia'].toString().isNotEmpty) ...[
          const SizedBox(height: 12),
          _section('💡 Recomendaciones', a['recomendaciones_ia'].toString(), AppColors.aar),
        ],

        if (a['mensaje_docente'] != null && a['mensaje_docente'].toString().isNotEmpty) ...[
          const SizedBox(height: 12),
          _section('👨‍🏫 Comunicado para el Docente', a['mensaje_docente'].toString(), AppColors.primary700),
        ],

        if (a['mensaje_representante'] != null && a['mensaje_representante'].toString().isNotEmpty) ...[
          const SizedBox(height: 12),
          _section('👨‍👩‍👦 Comunicado para el Representante', a['mensaje_representante'].toString(), AppColors.success),
        ],

        // Cambiar estado
        const SizedBox(height: 20),
        const Text('Actualizar estado', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final estado in ['NUEVA', 'VISTA', 'NOTIFICADA', 'RESUELTA'])
            OutlinedButton(
              onPressed: () => _cambiarEstado(estado),
              style: OutlinedButton.styleFrom(
                backgroundColor: a['estado'] == estado ? AppColors.primary.withOpacity(0.1) : null,
                side: BorderSide(
                  color: a['estado'] == estado ? AppColors.primary : AppColors.divider,
                ),
              ),
              child: Text(estado, style: const TextStyle(fontSize: 12)),
            ),
        ]),
        const SizedBox(height: 24),
      ]),
    );
  }

  Widget _section(String title, String content, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.15)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: color)),
        const SizedBox(height: 8),
        Text(content, style: const TextStyle(fontSize: 13, height: 1.5)),
      ]),
    );
  }
}
