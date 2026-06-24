import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../models/deber.dart';
import '../../providers/deber_provider.dart';
import '../../widgets/common_widgets.dart';

class EntregasScreen extends StatefulWidget {
  final int deberId;
  const EntregasScreen({super.key, required this.deberId});

  @override
  State<EntregasScreen> createState() => _EntregasScreenState();
}

class _EntregasScreenState extends State<EntregasScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DeberProvider>().fetchEntregas(widget.deberId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final prov = context.watch<DeberProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Entregas')),
      body: prov.isLoading
          ? const LoadingWidget(message: 'Cargando entregas...')
          : prov.errorMessage.isNotEmpty
              ? ErrorDisplay(message: prov.errorMessage, onRetry: () => context.read<DeberProvider>().fetchEntregas(widget.deberId))
              : prov.entregas.isEmpty
                  ? const EmptyState(message: 'Sin entregas aún', icon: Icons.assignment_late_outlined)
                  : ListView.separated(
                      padding: const EdgeInsets.all(12),
                      itemCount: prov.entregas.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (ctx, i) => _EntregaCard(
                        entrega: prov.entregas[i],
                        onCalificar: () => _showCalificarDialog(ctx, prov.entregas[i]),
                      ),
                    ),
    );
  }

  void _showCalificarDialog(BuildContext context, DeberEntrega entrega) {
    final notaCtrl = TextEditingController(
        text: entrega.calificacion?.toStringAsFixed(1) ?? '');
    final retro = TextEditingController(text: entrega.retroalimentacion);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Calificar — ${entrega.estudianteNombre}'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
            controller: notaCtrl,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Nota (0 – 10)', border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: retro,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Retroalimentación', border: OutlineInputBorder(),
            ),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          ElevatedButton(
            onPressed: () async {
              final nota = double.tryParse(notaCtrl.text);
              if (nota == null || nota < 0 || nota > 10) return;
              Navigator.pop(ctx);
              await context.read<DeberProvider>().calificarEntrega(
                    entrega.id, nota, retro.text);
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
  }
}

class _EntregaCard extends StatelessWidget {
  final DeberEntrega entrega;
  final VoidCallback onCalificar;

  const _EntregaCard({required this.entrega, required this.onCalificar});

  @override
  Widget build(BuildContext context) {
    Color estadoColor;
    switch (entrega.estado) {
      case 'revisado': estadoColor = AppColors.success; break;
      case 'entregado': estadoColor = AppColors.primary; break;
      case 'tarde': estadoColor = AppColors.warning; break;
      default: estadoColor = AppColors.textMuted;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: AppColors.primary.withOpacity(0.1),
              child: Text(
                entrega.estudianteNombre.isNotEmpty ? entrega.estudianteNombre[0].toUpperCase() : '?',
                style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(entrega.estudianteNombre,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                Text('Entregado: ${entrega.fechaEntrega.day.toString().padLeft(2,'0')}/${entrega.fechaEntrega.month.toString().padLeft(2,'0')}/${entrega.fechaEntrega.year}',
                    style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
              ]),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: estadoColor.withOpacity(0.1), borderRadius: BorderRadius.circular(6),
              ),
              child: Text(entrega.estado,
                  style: TextStyle(fontSize: 11, color: estadoColor, fontWeight: FontWeight.bold)),
            ),
          ]),
          if (entrega.comentario.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8, left: 46),
              child: Text(entrega.comentario,
                  style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
            ),
          if (entrega.calificacion != null)
            Padding(
              padding: const EdgeInsets.only(top: 6, left: 46),
              child: Text('Nota: ${entrega.calificacion!.toStringAsFixed(1)} / 10',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.aar)),
            ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: onCalificar,
              icon: const Icon(Icons.grade_outlined, size: 16),
              label: Text(entrega.calificacion != null ? 'Editar nota' : 'Calificar'),
            ),
          ),
        ]),
      ),
    );
  }
}
