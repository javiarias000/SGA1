import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_app/providers/student_provider.dart';
import 'package:mobile_app/screens/student_form_screen.dart';

class StudentsListScreen extends StatefulWidget {
  const StudentsListScreen({super.key});

  @override
  State<StudentsListScreen> createState() => _StudentsListScreenState();
}

class _StudentsListScreenState extends State<StudentsListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<StudentProvider>(context, listen: false).fetchStudents();
    });
  }

  @override
  Widget build(BuildContext context) {
    final studentProvider = Provider.of<StudentProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Students'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const StudentFormScreen()),
              );
            },
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
                : studentProvider.students.isEmpty
                    ? const Text('No students available.')
                    : ListView.builder(
                        itemCount: studentProvider.students.length,
                        itemBuilder: (context, index) {
                          final student = studentProvider.students[index];
                          return Card(
                            margin: const EdgeInsets.all(8.0),
                            child: ListTile(
                              title: Text(
                                'Name: ${student.name ?? student.usuario.nombre}',
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Email: ${student.usuario.email}'),
                                  Text('Grade: ${student.gradeLevelName ?? "N/A"}'),
                                  Text('Teacher: ${student.teacherFullName ?? "N/A"}'),
                                ],
                              ),
                              onTap: () {
                                GoRouter.of(context).go('/students/${student.id}');
                              },
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}