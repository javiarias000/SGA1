import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common_widgets.dart';

class SecretariaScreen extends StatefulWidget {
  const SecretariaScreen({super.key});

  @override
  State<SecretariaScreen> createState() => _SecretariaScreenState();
}

class _SecretariaScreenState extends State<SecretariaScreen> {
  List<dynamic> _solicitudes = [];
  bool _loading = true;
  String _error = '';
  String _estadoFiltro = '';
  final _searchCtrl = TextEditingController();

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
      final data = await api.fetchSolicitudesSecretaria(
        estado: _estadoFiltro.isEmpty ? null : _estadoFiltro,
        busqueda: _searchCtrl.text.isEmpty ? null : _searchCtrl.text,
        authToken: auth.authToken,
      );
      setState(() => _solicitudes = data);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Color _colorEstado(String estado) {
    switch (estado) {
      case 'APROBADA': return AppColors.success;
      case 'RECHAZADA': return AppColors.error;
      case 'EN_REVISION': return AppColors.aar;
      case 'NOVEDAD': return AppColors.warning;
      default: return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Panel Secretaría')),
      body: Column(children: [
        // Filtros
        Container(
          color: Colors.white,
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            TextField(
              controller: _searchCtrl,
              decoration: InputDecoration(
                hintText: 'Buscar por nombre o cédula...',
                prefixIcon: const Icon(Icons.search),
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
                suffixIcon: IconButton(icon: const Icon(Icons.send), onPressed: _load),
              ),
              onSubmitted: (_) => _load(),
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: [
                for (final e in ['', 'PENDIENTE', 'EN_REVISION', 'NOVEDAD', 'APROBADA', 'RECHAZADA'])
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(e.isEmpty ? 'Todas' : e, style: const TextStyle(fontSize: 11)),
                      selected: _estadoFiltro == e,
                      onSelected: (_) { setState(() => _estadoFiltro = e); _load(); },
                      selectedColor: AppColors.primary.withOpacity(0.15),
                    ),
                  ),
              ]),
            ),
          ]),
        ),
        const Divider(height: 1),
        Expanded(
          child: _loading
              ? const LoadingWidget()
              : _error.isNotEmpty
                  ? ErrorDisplay(message: _error, onRetry: _load)
                  : _solicitudes.isEmpty
                      ? const EmptyState(message: 'No hay solicitudes')
                      : ListView.builder(
                          padding: const EdgeInsets.all(8),
                          itemCount: _solicitudes.length,
                          itemBuilder: (ctx, i) => _buildRow(_solicitudes[i]),
                        ),
        ),
      ]),
    );
  }

  Widget _buildRow(dynamic sol) {
    final estado = sol['estado']?.toString() ?? '';
    final color = _colorEstado(estado);
    final novedadIa = sol['tiene_novedades_ia'] == true;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.1),
          child: Text('${sol['anio_solicitado'] ?? '?'}°',
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13)),
        ),
        title: Row(children: [
          Expanded(
            child: Text(sol['nombre_completo']?.toString() ?? '',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          ),
          if (novedadIa) const Icon(Icons.warning_amber, color: AppColors.warning, size: 16),
        ]),
        subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(sol['cedula']?.toString() ?? '', style: const TextStyle(fontSize: 11)),
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              margin: const EdgeInsets.only(top: 3),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(4),
              ),
              child: Text(estado, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
            ),
          ]),
        ]),
        trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
        onTap: () => context.push('/matriculas/secretaria/${sol['id']}'),
      ),
    );
  }
}
