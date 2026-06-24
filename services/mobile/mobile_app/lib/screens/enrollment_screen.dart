import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/enrollment_provider.dart';
import 'package:mobile_app/providers/student_provider.dart';
import 'package:mobile_app/providers/clase_provider.dart';
import 'package:mobile_app/models/clase.dart';

class EnrollmentScreen extends StatefulWidget {
  final int studentId;

  const EnrollmentScreen({super.key, required this.studentId});

  @override
  State<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends State<EnrollmentScreen> {
  int? _selectedClaseId;
  String _selectedTipoMateria = 'TEORICA';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<EnrollmentProvider>(context, listen: false).fetchEnrollments(widget.studentId);
    });
  }

  Future<void> _submit() async {
    if (_selectedClaseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a class')),
      );
      return;
    }

    final enrollmentProvider = Provider.of<EnrollmentProvider>(context, listen: false);
    final data = {
      'estudiante': widget.studentId,
      'clase': _selectedClaseId,
      'tipo_materia': _selectedTipoMateria,
      'estado': 'ACTIVO',
    };

    try {
      await enrollmentProvider.enrollStudent(data);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Student enrolled successfully')),
      );
      await enrollmentProvider.fetchEnrollments(widget.studentId);
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Enrollment failed: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final enrollmentProvider = Provider.of<EnrollmentProvider>(context);
    final claseProvider = Provider.of<ClaseProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Enroll Student')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Select Class', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            DropdownButton<int>(
              isExpanded: true,
              value: _selectedClaseId,
              items: claseProvider.clases.map((clase) {
                return DropdownMenuItem<int>(
                  value: clase.id,
                  child: Text('${clase.name} (${clase.subject?.name})'),
                );
              }).toList(),
              onChanged: (val) => setState(() => _selectedClaseId = val),
            ),
            const SizedBox(height: 20),
            const Text('Materia Type', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            DropdownButton<String>(
              isExpanded: true,
              value: _selectedTipoMateria,
              items: ['TEORICA', 'AGRUPACION', 'INSTRUMENTO'].map((type) {
                return DropdownMenuItem<String>(
                  value: type,
                  child: Text(type),
                );
              }).toList(),
              onChanged: (val) => setState(() => _selectedTipoMateria = val!),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submit,
                child: const Text('Confirm Enrollment'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
