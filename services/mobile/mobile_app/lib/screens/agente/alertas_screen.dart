import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common_widgets.dart';

class AlertasScreen extends StatefulWidget {
  const AlertasScreen({super.key});

  @override
  State<AlertasScreen> createState() => _AlertasScreenState();
}

class _AlertasScreenState extends State<AlertasScreen> {
  List<dynamic> _alertas = [];
  bool _loading = true;
  String _error = '';
  String _sevFiltro = '';

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
      final data = await api.fetchAlertas(
        severidad: _sevFiltro.isEmpty ? null : _sevFiltro,
        authToken: auth.authToken,
      );
      setState(() => _alertas = data);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _lanzarAnalisis() async {
    // Lanzar análisis manual de todos los estudiantes
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Análisis completo encolado. Resultados en minutos.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final criticas = _alertas.where((a) => a['severidad'] == 'CRITICA').length;
    final nuevas = _alertas.where((a) => a['estado'] == 'NUEVA').length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Alertas Académicas'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: Column(children: [
        // Stats
        Container(
          color: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(children: [
            Expanded(child: _stat('Total', _alertas.length.toString(), AppColors.primary)),
            Expanded(child: _stat('Críticas', criticas.toString(), AppColors.error)),
            Expanded(child: _stat('Sin leer', nuevas.toString(), AppColors.warning)),
          ]),
        ),

        // Filtros
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            for (final sev in ['', 'CRITICA', 'ALTA', 'MEDIA', 'BAJA'])
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: FilterChip(
                  label: Text(sev.isEmpty ? 'Todas' : sev, style: const TextStyle(fontSize: 11)),
                  selected: _sevFiltro == sev,
                  onSelected: (_) { setState(() => _sevFiltro = sev); _load(); },
                  selectedColor: AppColors.primary.withOpacity(0.15),
                ),
              ),
          ]),
        ),
        const Divider(height: 1),

        Expanded(
          child: _loading
              ? const LoadingWidget()
              : _error.isNotEmpty
                  ? ErrorDisplay(message: _error, onRetry: _load)
                  : _alertas.isEmpty
                      ? const EmptyState(
                          message: 'No hay alertas activas', icon: Icons.check_circle_outline)
                      : ListView.builder(
                          padding: const EdgeInsets.all(8),
                          itemCount: _alertas.length,
                          itemBuilder: (ctx, i) => _buildRow(_alertas[i]),
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

  Widget _buildRow(dynamic alerta) {
    final sev = alerta['severidad']?.toString() ?? '';
    final estado = alerta['estado']?.toString() ?? '';
    final isNueva = estado == 'NUEVA';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      color: isNueva ? const Color(0xFFFFFBEB) : Colors.white,
      child: ListTile(
        leading: SeverityChip(severidad: sev),
        title: Row(children: [
          Expanded(
            child: Text(alerta['estudiante']?['nombre']?.toString() ?? '',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          ),
          if (isNueva)
            Container(
              width: 8, height: 8,
              decoration: const BoxDecoration(color: AppColors.warning, shape: BoxShape.circle),
            ),
        ]),
        subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(alerta['tipo_display']?.toString() ?? '', style: const TextStyle(fontSize: 11)),
          if (alerta['materia'] != null)
            Text('📚 ${alerta['materia']}', style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
          if (alerta['promedio_detectado'] != null)
            Text('Promedio: ${alerta['promedio_detectado']}',
                style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
        ]),
        trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
        onTap: () => context.push('/agente/alertas/${alerta['id']}'),
      ),
    );
  }
}
