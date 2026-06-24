import 'package:flutter/material.dart';
import '../core/theme.dart';

// ─── Loading / Error ─────────────────────────────────────────────────────────

class LoadingWidget extends StatelessWidget {
  final String? message;
  const LoadingWidget({super.key, this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const CircularProgressIndicator(color: AppColors.primary),
        if (message != null) ...[
          const SizedBox(height: 12),
          Text(message!, style: const TextStyle(color: AppColors.textMuted)),
        ],
      ]),
    );
  }
}

class ErrorDisplay extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  const ErrorDisplay({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 48),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.textMuted)),
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Reintentar'),
            ),
          ],
        ]),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String message;
  final IconData icon;
  const EmptyState({super.key, required this.message, this.icon = Icons.inbox_outlined});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 56, color: AppColors.divider),
        const SizedBox(height: 12),
        Text(message, style: const TextStyle(color: AppColors.textMuted)),
      ]),
    );
  }
}

// ─── Stat Card ───────────────────────────────────────────────────────────────

class StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.color = AppColors.primary,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: color, size: 22),
        const SizedBox(height: 8),
        Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
      ]),
    );
  }
}

// ─── Grade Badge ─────────────────────────────────────────────────────────────

class GradeBadge extends StatelessWidget {
  final double? nota;
  const GradeBadge({super.key, this.nota});

  Color get _color {
    if (nota == null) return AppColors.textMuted;
    if (nota! >= 9) return AppColors.dar;
    if (nota! >= 7) return AppColors.aar;
    if (nota! > 4) return AppColors.paar;
    return AppColors.naar;
  }

  String get _label {
    if (nota == null) return '—';
    if (nota! >= 9) return 'DAR';
    if (nota! >= 7) return 'AAR';
    if (nota! > 4) return 'PAAR';
    return 'NAAR';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: _color.withOpacity(0.3)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Text(
          nota != null ? nota!.toStringAsFixed(2) : '—',
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: _color),
        ),
        const SizedBox(width: 5),
        Text(_label, style: TextStyle(fontSize: 10, color: _color)),
      ]),
    );
  }
}

// ─── Section Header ──────────────────────────────────────────────────────────

class SectionHeader extends StatelessWidget {
  final String title;
  final Widget? trailing;
  const SectionHeader({super.key, required this.title, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(children: [
        Expanded(
          child: Text(title, style: Theme.of(context).textTheme.titleMedium),
        ),
        if (trailing != null) trailing!,
      ]),
    );
  }
}

// ─── Info Row ────────────────────────────────────────────────────────────────

class InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const InfoRow({super.key, required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Icon(icon, size: 16, color: AppColors.textMuted),
        const SizedBox(width: 8),
        Text('$label: ', style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
        Expanded(
          child: Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ),
      ]),
    );
  }
}

// ─── CB AppBar ───────────────────────────────────────────────────────────────

PreferredSizeWidget cbAppBar(String title, {List<Widget>? actions, bool showBack = true}) {
  return AppBar(
    title: Text(title),
    backgroundColor: AppColors.primary,
    foregroundColor: Colors.white,
    actions: actions,
    automaticallyImplyLeading: showBack,
  );
}

// ─── Alert Severity Chip ─────────────────────────────────────────────────────

class SeverityChip extends StatelessWidget {
  final String severidad;
  const SeverityChip({super.key, required this.severidad});

  Color get _color {
    switch (severidad) {
      case 'CRITICA': return AppColors.naar;
      case 'ALTA': return const Color(0xFFEA580C);
      case 'MEDIA': return AppColors.warning;
      default: return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: _color.withOpacity(0.3)),
      ),
      child: Text(severidad,
          style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: _color)),
    );
  }
}
