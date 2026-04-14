import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/horario_provider.dart';
import 'package:mobile_app/models/horario.dart'; // Import Horario model

class HorarioDetailScreen extends StatefulWidget {
  final int horarioId;
  const HorarioDetailScreen({super.key, required this.horarioId});

  @override
  State<HorarioDetailScreen> createState() => _HorarioDetailScreenState();
}

class _HorarioDetailScreenState extends State<HorarioDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<HorarioProvider>(context, listen: false).fetchHorarioDetail(widget.horarioId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final horarioProvider = Provider.of<HorarioProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Horario Details'),
      ),
      body: Center(
        child: horarioProvider.isLoading
            ? const CircularProgressIndicator()
            : horarioProvider.errorMessage.isNotEmpty
                ? Text(
                    horarioProvider.errorMessage,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  )
                : horarioProvider.selectedHorario == null
                    ? const Text('Horario not found.')
                    : _buildHorarioDetails(horarioProvider.selectedHorario!),
      ),
    );
  }

  Widget _buildHorarioDetails(Horario horario) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Day: ${horario.dia}',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text('Time: ${horario.hora}', style: const TextStyle(fontSize: 16)),
          Text('Room: ${horario.aula}', style: const TextStyle(fontSize: 16)),
          const Divider(),
          Text('Course: ${horario.curso?.level} ${horario.curso?.section ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Teacher: ${horario.docente?.nombre ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Class Subject: ${horario.clase?.name ?? "N/A"}', style: const TextStyle(fontSize: 16)),
        ],
      ),
    );
  }
}