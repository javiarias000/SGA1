import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../providers/auth_provider.dart';

class InformeScreen extends StatefulWidget {
  const InformeScreen({super.key});

  @override
  State<InformeScreen> createState() => _InformeScreenState();
}

class _InformeScreenState extends State<InformeScreen> {
  final _ctrl = TextEditingController();
  Map<String, dynamic>? _resultado;
  bool _loading = false;
  String _error = '';

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _mejorar() async {
    final texto = _ctrl.text.trim();
    if (texto.length < 20) {
      setState(() => _error = 'El texto debe tener al menos 20 caracteres.');
      return;
    }
    setState(() { _loading = true; _error = ''; _resultado = null; });
    try {
      final api = context.read<ApiService>();
      final auth = context.read<AuthProvider>();
      final data = await api.mejorarInforme(texto, authToken: auth.authToken);
      setState(() => _resultado = data);
    } catch (e) {
      setState(() => _error = e.toString().replaceAll('Exception: ', ''));
    } finally {
      setState(() => _loading = false);
    }
  }

  void _copiar() {
    if (_resultado == null) return;
    Clipboard.setData(ClipboardData(text: _resultado!['texto_mejorado'].toString()));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Texto copiado al portapapeles')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Asistente de Informes')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          // Instrucciones
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.05),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Row(children: [
              Icon(Icons.smart_toy_outlined, color: AppColors.primary, size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Escribe tu informe de clase y el agente IA lo mejorará manteniendo tu contenido intacto.',
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
              ),
            ]),
          ),
          const SizedBox(height: 16),

          // Input
          TextField(
            controller: _ctrl,
            maxLines: 8,
            decoration: const InputDecoration(
              labelText: 'Tu informe de clase',
              alignLabelWithHint: true,
              hintText: 'Escribe aquí los temas trabajados, rendimiento del estudiante, observaciones...',
            ),
          ),
          const SizedBox(height: 12),

          if (_error.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(10),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.05),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.error.withOpacity(0.2)),
              ),
              child: Text(_error, style: const TextStyle(color: AppColors.error, fontSize: 12)),
            ),

          SizedBox(
            height: 48,
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : ElevatedButton.icon(
                    onPressed: _mejorar,
                    icon: const Icon(Icons.auto_fix_high),
                    label: const Text('Mejorar con IA'),
                  ),
          ),

          if (_resultado != null) ...[
            const SizedBox(height: 24),
            const Text('✨ Versión mejorada',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 10),

            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.04),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.primary.withOpacity(0.12)),
              ),
              child: Text(
                _resultado!['texto_mejorado']?.toString() ?? '',
                style: const TextStyle(fontSize: 13, height: 1.6),
              ),
            ),

            if (_resultado!['sugerencias_ia'] != null &&
                _resultado!['sugerencias_ia'].toString().isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.divider),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('💬 Cambios realizados',
                      style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                  const SizedBox(height: 6),
                  Text(_resultado!['sugerencias_ia'].toString(),
                      style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                ]),
              ),
            ],

            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: _copiar,
              icon: const Icon(Icons.copy, size: 16),
              label: const Text('Copiar texto mejorado'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () { setState(() { _resultado = null; _ctrl.clear(); }); },
              child: const Text('Limpiar y empezar de nuevo'),
            ),
          ],
          const SizedBox(height: 40),
        ]),
      ),
    );
  }
}
