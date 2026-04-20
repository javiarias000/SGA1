import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/student_provider.dart';
import 'package:mobile_app/models/student.dart';
import 'package:mobile_app/screens/student_form_screen.dart';
import 'package:mobile_app/screens/enrollment_screen.dart';
import 'package:mobile_app/screens/grade_entry_screen.dart';
import 'package:mobile_app/screens/attendance_screen.dart';

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
        actions: [
          if (studentProvider.selectedStudent != null)
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => StudentFormScreen(student: studentProvider.selectedStudent),
                  ),
                );
              },
            ),
          if (studentProvider.selectedStudent != null)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _confirmDelete(studentProvider),
            ),
        ],
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

  void _confirmDelete(StudentProvider provider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Student'),
        content: const Text('Are you sure you want to delete this student?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              await provider.deleteStudent(provider.selectedStudent!.id);
              if (mounted) {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Student deleted successfully')),
                );
                // Go back to list since student is gone
                Provider.of<StudentProvider>(context, listen: false).clearSelection();
                Navigator.pop(context);
              }
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
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
            'Name: ${student.name ?? student.usuario?.nombre ?? "N/A"}',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text('Email: ${student.usuario?.email ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Phone: ${student.usuario?.phone ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Cedula: ${student.usuario?.cedula ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Role: ${student.usuario?.rol ?? "N/A"}', style: const TextStyle(fontSize: 16)),
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
          const SizedBox(height: 10),
          Text('Notes: ${student.notes ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => EnrollmentScreen(studentId: student.id),
                ),
              );
            },
            icon: const Icon(Icons.school),
            label: const Text('Enroll in Class'),
          ),
          const SizedBox(height: 10),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => GradeEntryScreen(
                    studentId: student.id,
                    subject: 'Matemáticas', // Fixed for now, usually selected from enrollments
                    parcial: '1P',
                    quimestre: 'Q1',
                  ),
                ),
              );
            },
            icon: const Icon(Icons.grade),
            label: const Text('Enter Grades'),
          ),
          const SizedBox(height: 10),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => AttendanceScreen(studentId: student.id),
                ),
              );
            },
            icon: const Icon(Icons.calendar_today),
            label: const Text('View Attendance'),
          ),
        ],
      ),
    );
  }
}

extension on DateTime {
  String toShortDateString() {
    return '$year-${month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
  }
}