import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/deber_provider.dart';
import '../../models/deber.dart';
import '../../widgets/common_widgets.dart';

class DeberesScreen extends StatefulWidget {
  const DeberesScreen({super.key});

  @override
  State<DeberesScreen> createState() => _DeberesScreenState();
}

class _DeberesScreenState extends State<DeberesScreen> {
  String _estadoFilter = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  void _load() {
    final auth = context.read<AuthProvider>();
    final prov = context.read<DeberProvider>();
    if (auth.userRole == 'ESTUDIANTE' && auth.studentId != null) {
      prov.fetchMisEntregas(auth.studentId!);
    } else {
      prov.fetchDeberes(estado: _estadoFilter.isEmpty ? null : _estadoFilter);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final prov = context.watch<DeberProvider>();
    final isEstudiante = auth.userRole == 'ESTUDIANTE';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Deberes'),
        actions: [
          if (!isEstudiante)
            IconButton(
              icon: const Icon(Icons.add),
              onPressed: () => context.push('/deberes/nuevo').then((_) => _load()),
            ),
        ],
      ),
      body: Column(children: [
        if (!isEstudiante)
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: DropdownButtonFormField<String>(
              value: _estadoFilter,
              decoration: const InputDecoration(
                labelText: 'Estado', isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem(value: '', child: Text('Todos')),
                ...['borrador', 'activo', 'cerrado'].map((e) =>
                    DropdownMenuItem(value: e, child: Text(e[0].toUpperCase() + e.substring(1)))),
              ],
              onChanged: (v) => setState(() { _estadoFilter = v ?? ''; _load(); }),
            ),
          ),

        Expanded(
          child: prov.isLoading
              ? const LoadingWidget(message: 'Cargando deberes...')
              : prov.errorMessage.isNotEmpty
                  ? ErrorDisplay(message: prov.errorMessage, onRetry: _load)
                  : isEstudiante
                      ? _buildEntregasList(prov.misEntregas)
                      : _buildDeberesList(prov.deberes, context),
        ),
      ]),
    );
  }

  Widget _buildDeberesList(List<Deber> deberes, BuildContext context) {
    if (deberes.isEmpty) {
      return const EmptyState(message: 'Sin deberes registrados', icon: Icons.assignment_outlined);
    }
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: deberes.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (ctx, i) => _DeberCard(
        deber: deberes[i],
        onTap: () => context.push('/deberes/${deberes[i].id}/entregas').then((_) => _load()),
        onDelete: () => _confirmDelete(deberes[i].id),
      ),
    );
  }

  Widget _buildEntregasList(List<DeberEntrega> entregas) {
    if (entregas.isEmpty) {
      return const EmptyState(message: 'Sin deberes asignados', icon: Icons.assignment_outlined);
    }
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: entregas.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (ctx, i) => _EntregaCard(entrega: entregas[i]),
    );
  }

  Future<void> _confirmDelete(int id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Eliminar deber'),
        content: const Text('¿Seguro que quieres eliminar este deber?'),
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
      await context.read<DeberProvider>().deleteDeber(id);
    }
  }
}

class _DeberCard extends StatelessWidget {
  final Deber deber;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _DeberCard({required this.deber, required this.onTap, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final vencido = deber.estaVencido;
    final estadoColor = deber.estado == 'activo'
        ? AppColors.success
        : deber.estado == 'cerrado'
            ? AppColors.textMuted
            : AppColors.warning;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text(deber.titulo,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: estadoColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: estadoColor.withOpacity(0.3)),
                ),
                child: Text(deber.estado,
                    style: TextStyle(fontSize: 11, color: estadoColor, fontWeight: FontWeight.bold)),
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline, size: 18, color: AppColors.textMuted),
                onPressed: onDelete,
              ),
            ]),
            if (deber.descripcion.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(deber.descripcion,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
              ),
            const SizedBox(height: 8),
            Row(children: [
              Icon(Icons.calendar_today, size: 13,
                  color: vencido ? AppColors.error : AppColors.textMuted),
              const SizedBox(width: 4),
              Text(
                'Entrega: ${DateFormat('dd/MM/yyyy HH:mm').format(deber.fechaEntrega)}',
                style: TextStyle(
                    fontSize: 11,
                    color: vencido ? AppColors.error : AppColors.textMuted),
              ),
              const Spacer(),
              Text(
                '${deber.entregasCompletadas} entregas · ${deber.porcentajeEntrega.toStringAsFixed(0)}%',
                style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
              ),
            ]),
          ]),
        ),
      ),
    );
  }
}

class _EntregaCard extends StatelessWidget {
  final DeberEntrega entrega;
  const _EntregaCard({required this.entrega});

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
            Expanded(
              child: Text(entrega.deberTitulo,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: estadoColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(entrega.estado,
                  style: TextStyle(fontSize: 11, color: estadoColor, fontWeight: FontWeight.bold)),
            ),
          ]),
          const SizedBox(height: 6),
          if (entrega.calificacion != null)
            Row(children: [
              const Icon(Icons.grade, size: 16, color: AppColors.aar),
              const SizedBox(width: 4),
              Text('Calificación: ${entrega.calificacion!.toStringAsFixed(1)} / 10',
                  style: const TextStyle(fontSize: 12, color: AppColors.aar, fontWeight: FontWeight.w600)),
            ]),
          if (entrega.retroalimentacion.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Retroalimentación: ${entrega.retroalimentacion}',
                  style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
            ),
        ]),
      ),
    );
  }
}
