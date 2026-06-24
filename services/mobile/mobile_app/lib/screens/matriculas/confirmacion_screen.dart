import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';

class ConfirmacionScreen extends StatelessWidget {
  final String codigo;
  final String nombre;
  const ConfirmacionScreen({super.key, required this.codigo, required this.nombre});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surface,
      appBar: AppBar(title: const Text('Solicitud Enviada'), automaticallyImplyLeading: false),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(children: [
          const SizedBox(height: 20),
          Container(
            width: 80, height: 80,
            decoration: BoxDecoration(
              color: AppColors.success.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.check_circle, size: 50, color: AppColors.success),
          ),
          const SizedBox(height: 16),
          Text('¡Solicitud enviada!', style: Theme.of(context).textTheme.displayMedium),
          const SizedBox(height: 8),
          Text(nombre, style: const TextStyle(color: AppColors.textMuted, fontSize: 14)),
          const SizedBox(height: 24),

          // Código
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.primary.withOpacity(0.2)),
            ),
            child: Column(children: [
              const Text('Código de seguimiento',
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
              const SizedBox(height: 8),
              Text(codigo, style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
              )),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: codigo));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Código copiado al portapapeles')),
                  );
                },
                icon: const Icon(Icons.copy, size: 16),
                label: const Text('Copiar código'),
              ),
            ]),
          ),

          const SizedBox(height: 24),
          const Text('Próximos pasos', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
          const SizedBox(height: 12),
          ...[
            '1. El equipo revisará tu solicitud',
            '2. Se analizarán los documentos automáticamente',
            '3. Recibirás un correo con el resultado',
            '4. Si hay novedades, se te pedirá corregir documentos',
          ].map((s) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              const Icon(Icons.arrow_right, color: AppColors.gold),
              Expanded(child: Text(s, style: const TextStyle(fontSize: 13))),
            ]),
          )),

          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => context.go('/'),
              child: const Text('Volver al inicio'),
            ),
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () => context.push('/matriculas/seguimiento'),
            child: const Text('Consultar estado de mi solicitud'),
          ),
        ]),
      ),
    );
  }
}
