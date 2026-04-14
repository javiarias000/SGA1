import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/student_provider.dart';
import 'package:mobile_app/models/student.dart'; // Import Student model

class StudentDetailScreen extends StatefulWidget {
  final int studentId;
  const StudentDetailScreen({super.key, required this.studentId});

  @override
  State<StudentDetailScreen> createState() => _StudentDetailScreenState();
}

class _StudentDetailScreenState extends State<StudentDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<StudentProvider>(context, listen: false).fetchStudentDetail(widget.studentId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final studentProvider = Provider.of<StudentProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Student Details'),
      ),
      body: Center(
        child: studentProvider.isLoading
            ? const CircularProgressIndicator()
            : studentProvider.errorMessage.isNotEmpty
                ? Text(
                    studentProvider.errorMessage,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  )
                : studentProvider.selectedStudent == null
                    ? const Text('Student not found.')
                    : _buildStudentDetails(studentProvider.selectedStudent!),
      ),
    );
  }

  Widget _buildStudentDetails(Student student) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Name: ${student.name ?? student.usuario.nombre}',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text('Email: ${student.usuario.email}', style: const TextStyle(fontSize: 16)),
          Text('Phone: ${student.usuario.phone ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Cedula: ${student.usuario.cedula ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Role: ${student.usuario.rol}', style: const TextStyle(fontSize: 16)),
          const Divider(),
          Text('Parent Name: ${student.parentName ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Parent Email: ${student.parentEmail ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Parent Phone: ${student.parentPhone ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          const Divider(),
          Text('Grade Level: ${student.gradeLevelName ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Teacher: ${student.teacherFullName ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          const Divider(),
          Text('Active: ${student.active ? "Yes" : "No"}', style: const TextStyle(fontSize: 16)),
          Text('Registration Code: ${student.registrationCode ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Created At: ${student.createdAt.toLocal().toShortDateString()}', style: const TextStyle(fontSize: 16)),
          // You might add an Image.network here for student.photo if the URL is valid
          // if (student.photo != null && student.photo!.isNotEmpty)
          //   Image.network(student.photo!),
          const SizedBox(height: 10),
          Text('Notes: ${student.notes ?? "N/A"}', style: const TextStyle(fontSize: 16)),
        ],
      ),
    );
  }
}

// Extension to format DateTime to a short date string
extension on DateTime {
  String toShortDateString() {
    return '$year-${month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
  }
}