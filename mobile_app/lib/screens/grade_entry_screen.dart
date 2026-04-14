import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/grade_provider.dart';
import 'package:mobile_app/providers/student_provider.dart';

class GradeEntryScreen extends StatefulWidget {
  final int studentId;
  final String subject;
  final String parcial;
  final String quimestre;

  const GradeEntryScreen({
    super.key,
    required this.studentId,
    required this.subject,
    required this.parcial,
    required this.quimestre,
  });

  @override
  State<GradeEntryScreen> createState() => _GradeEntryScreenState();
}

class _GradeEntryScreenState extends State<GradeEntryScreen> {
  late TextEditingController _gradeController;
  int? _selectedTipoAporteId;

  @override
  void initState() {
    super.initState();
    _gradeController = TextEditingController();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<GradeProvider>(context, listen: false)
          .fetchGrades(widget.studentId, widget.subject, widget.parcial, widget.quimestre);
    });
  }

  @override
  void dispose() {
    _gradeController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_selectedTipoAporteId == null || _gradeController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a type and enter a grade')),
      );
      return;
    }

    final gradeProvider = Provider.of<GradeProvider>(context, listen: false);
    try {
      await gradeProvider.saveGrade(
        studentId: widget.studentId,
        subject: widget.subject,
        parcial: widget.parcial,
        tipoAporteId: _selectedTipoAporteId!,
        calificacion: double.parse(_gradeController.text),
      );
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Grade saved successfully')),
      );
      await gradeProvider.fetchGrades(widget.studentId, widget.subject, widget.parcial, widget.quimestre);
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error saving grade: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final gradeProvider = Provider.of<GradeProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Enter Grade')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Student ID: ${widget.studentId}'),
            Text('Subject: ${widget.subject}'),
            Text('Period: ${widget.parcial} (${widget.quimestre})'),
            const Divider(),
            const Text('Grade Value (0-10)', style: TextStyle(fontWeight: FontWeight.bold)),
            TextField(
              controller: _gradeController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'e.g. 8.5'),
            ),
            const SizedBox(height: 20),
            const Text('Aporte Type', style: TextStyle(fontWeight: FontWeight.bold)),
            // In a real app, this would be a list from the API.
            // For now, we use a simplified selection.
            DropdownButton<int>(
              value: _selectedTipoAporteId,
              items: [
                DropdownMenuItem(value: 1, child: Text('Exam')),
                DropdownMenuItem(value: 2, child: Text('Homework')),
                DropdownMenuItem(value: 3, child: Text('Participation')),
              ],
              onChanged: (val) => setState(() => _selectedTipoAporteId = val),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _save,
                child: const Text('Save Grade'),
              ),
            ),
            const SizedBox(height: 20),
            const Text('Current Grades:', style: TextStyle(fontWeight: FontWeight.bold)),
            Expanded(
              child: gradeProvider.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.builder(
                      itemCount: (gradeProvider.currentGrades['calificaciones'] as List?)?.length ?? 0,
                      itemBuilder: (context, index) {
                        final grade = gradeProvider.currentGrades['calificaciones'][index];
                        return ListTile(
                          title: Text(grade['tipo_aporte_nombre']),
                          trailing: Text(grade['calificacion'].toString()),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
