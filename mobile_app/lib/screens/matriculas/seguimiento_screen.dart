import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../widgets/common_widgets.dart';

class SeguimientoScreen extends StatefulWidget {
  const SeguimientoScreen({super.key});

  @override
  State<SeguimientoScreen> createState() => _SeguimientoScreenState();
}

class _SeguimientoScreenState extends State<SeguimientoScreen> {
  final _busCtrl = TextEditingController();
  Map<String, dynamic>? _solicitud;
  bool _loading = false;
  String _error = '';

  Future<void> _buscar() async {
    final q = _busCtrl.text.trim();
    if (q.isEmpty) return;
    setState(() { _loading = true; _error = ''; _solicitud = null; });
    try {
      final api = context.read<ApiService>();
      final data = await api.seguimientoMatricula(q);
      setState(() => _solicitud = data);
    } catch (e) {
      setState(() => _error = e.toString().replaceAll('Exception: ', ''));
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Seguimiento de Solicitud')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Ingresa tu código de seguimiento o cédula:',
              style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          TextField(
            controller: _busCtrl,
            decoration: const InputDecoration(
              labelText: 'Código UUID o número de cédula',
              prefixIcon: Icon(Icons.search),
            ),
            onSubmitted: (_) => _buscar(),
          ),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            onPressed: _loading ? null : _buscar,
            icon: _loading
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Icon(Icons.search),
            label: Text(_loading ? 'Buscando...' : 'Consultar estado'),
          ),

          if (_error.isNotEmpty) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.05),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.error.withOpacity(0.2)),
              ),
              child: Row(children: [
                const Icon(Icons.error_outline, color: AppColors.error, size: 18),
                const SizedBox(width: 8),
                Expanded(child: Text(_error, style: const TextStyle(color: AppColors.error, fontSize: 13))),
              ]),
            ),
          ],

          if (_solicitud != null) ...[
            const SizedBox(height: 20),
            _buildResultado(_solicitud!),
          ],
        ]),
      ),
    );
  }

  Widget _buildResultado(Map<String, dynamic> sol) {
    final estado = sol['estado']?.toString() ?? '';
    final Color color;
    final IconData icon;
    switch (estado) {
      case 'APROBADA': color = AppColors.success; icon = Icons.check_circle; break;
      case 'RECHAZADA': color = AppColors.error; icon = Icons.cancel; break;
      case 'EN_REVISION': color = AppColors.aar; icon = Icons.search; break;
      case 'NOVEDAD': color = AppColors.warning; icon = Icons.warning; break;
      default: color = AppColors.textMuted; icon = Icons.hourglass_empty;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(width: 12),
            Expanded(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(sol['nombre_completo']?.toString() ?? '',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                Container(
                  margin: const EdgeInsets.only(top: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(estado, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
                ),
              ],
            )),
          ]),
          const Divider(height: 20),
          InfoRow(icon: Icons.badge, label: 'Cédula', value: sol['cedula']?.toString() ?? ''),
          InfoRow(icon: Icons.school, label: 'Año', value: '${sol['anio_solicitado']}° año'),
          InfoRow(icon: Icons.music_note, label: 'Instrumento', value: sol['instrumento_elegido']?.toString() ?? ''),
          InfoRow(icon: Icons.calendar_today, label: 'Ciclo', value: sol['ciclo_lectivo']?.toString() ?? ''),
          if (sol['resumen_ia'] != null && sol['resumen_ia'].toString().isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.04),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('🤖 Análisis de documentos',
                    style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                const SizedBox(height: 6),
                Text(sol['resumen_ia'].toString(), style: const TextStyle(fontSize: 12)),
              ]),
            ),
          ],
          if (sol['notas_secretaria'] != null && sol['notas_secretaria'].toString().isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.warning.withOpacity(0.05),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.warning.withOpacity(0.2)),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Notas de secretaría',
                    style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                const SizedBox(height: 4),
                Text(sol['notas_secretaria'].toString(), style: const TextStyle(fontSize: 12)),
              ]),
            ),
          ],
        ]),
      ),
    );
  }
}
