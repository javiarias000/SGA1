import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/teacher_provider.dart';
import 'package:mobile_app/models/teacher.dart'; // Import Teacher model

class TeacherDetailScreen extends StatefulWidget {
  final int teacherId;
  const TeacherDetailScreen({super.key, required this.teacherId});

  @override
  State<TeacherDetailScreen> createState() => _TeacherDetailScreenState();
}

class _TeacherDetailScreenState extends State<TeacherDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<TeacherProvider>(context, listen: false).fetchTeacherDetail(widget.teacherId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final teacherProvider = Provider.of<TeacherProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Teacher Details'),
      ),
      body: Center(
        child: teacherProvider.isLoading
            ? const CircularProgressIndicator()
            : teacherProvider.errorMessage.isNotEmpty
                ? Text(
                    teacherProvider.errorMessage,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  )
                : teacherProvider.selectedTeacher == null
                    ? const Text('Teacher not found.')
                    : _buildTeacherDetails(teacherProvider.selectedTeacher!),
      ),
    );
  }

  Widget _buildTeacherDetails(Teacher teacher) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Name: ${teacher.fullName ?? teacher.usuario.nombre}',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text('Email: ${teacher.usuario.email}', style: const TextStyle(fontSize: 16)),
          Text('Phone: ${teacher.usuario.phone ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Cedula: ${teacher.usuario.cedula ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          Text('Role: ${teacher.usuario.rol}', style: const TextStyle(fontSize: 16)),
          const Divider(),
          Text('Specialization: ${teacher.specialization ?? "N/A"}', style: const TextStyle(fontSize: 16)),
          // You might add an Image.network here for teacher.photo if the URL is valid
          // if (teacher.photo != null && teacher.photo!.isNotEmpty)
          //   Image.network(teacher.photo!),
          const SizedBox(height: 10),
        ],
      ),
    );
  }
}