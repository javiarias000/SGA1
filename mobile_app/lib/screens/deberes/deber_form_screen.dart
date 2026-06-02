import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/deber_provider.dart';
import '../../providers/clase_provider.dart';
import '../../providers/auth_provider.dart';

class DeberFormScreen extends StatefulWidget {
  const DeberFormScreen({super.key});

  @override
  State<DeberFormScreen> createState() => _DeberFormScreenState();
}

class _DeberFormScreenState extends State<DeberFormScreen> {
  final _tituloCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  DateTime _fechaEntrega = DateTime.now().add(const Duration(days: 7));
  int? _claseId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ClaseProvider>().fetchClases();
    });
  }

  @override
  void dispose() {
    _tituloCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _fechaEntrega,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _fechaEntrega = picked);
    }
  }

  Future<void> _save() async {
    if (_tituloCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('El título es obligatorio.')),
      );
      return;
    }

    setState(() => _saving = true);
    final auth = context.read<AuthProvider>();
    final ok = await context.read<DeberProvider>().createDeber({
      'titulo': _tituloCtrl.text.trim(),
      'descripcion': _descCtrl.text.trim(),
      'fecha_entrega': _fechaEntrega.toIso8601String(),
      'teacher': auth.userId,
      if (_claseId != null) 'clase': _claseId,
      'estado': 'activo',
    });
    setState(() => _saving = false);
    if (mounted) {
      if (ok) {
        Navigator.of(context).pop(true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(context.read<DeberProvider>().errorMessage)),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final clases = context.watch<ClaseProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Nuevo Deber')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(children: [
          TextField(
            controller: _tituloCtrl,
            decoration: const InputDecoration(
              labelText: 'Título *',
              prefixIcon: Icon(Icons.title),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _descCtrl,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Descripción',
              prefixIcon: Icon(Icons.description),
              border: OutlineInputBorder(),
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 16),
          if (clases.isLoading)
            const LinearProgressIndicator()
          else
            DropdownButtonFormField<int>(
              value: _claseId,
              decoration: const InputDecoration(
                labelText: 'Clase (opcional)',
                prefixIcon: Icon(Icons.class_),
                border: OutlineInputBorder(),
              ),
              hint: const Text('Selecciona una clase'),
              items: clases.clases.map((c) {
                final name = c.subject?.name ?? c.name;
                return DropdownMenuItem<int>(value: c.id, child: Text(name));
              }).toList(),
              onChanged: (v) => setState(() => _claseId = v),
            ),
          const SizedBox(height: 16),
          InkWell(
            onTap: _pickDate,
            child: InputDecorator(
              decoration: const InputDecoration(
                labelText: 'Fecha de entrega',
                prefixIcon: Icon(Icons.calendar_today),
                border: OutlineInputBorder(),
              ),
              child: Text(
                '${_fechaEntrega.day.toString().padLeft(2, '0')}/'
                '${_fechaEntrega.month.toString().padLeft(2, '0')}/'
                '${_fechaEntrega.year}',
              ),
            ),
          ),
          const SizedBox(height: 28),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: _saving
                ? const Center(child: CircularProgressIndicator())
                : ElevatedButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text('Crear Deber'),
                  ),
          ),
        ]),
      ),
    );
  }
}
