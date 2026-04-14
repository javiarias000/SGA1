import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_app/providers/teacher_provider.dart';
import 'package:mobile_app/screens/teacher_form_screen.dart';

class TeachersListScreen extends StatefulWidget {
  const TeachersListScreen({super.key});

  @override
  State<TeachersListScreen> createState() => _TeachersListScreenState();
}

class _TeachersListScreenState extends State<TeachersListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<TeacherProvider>(context, listen: false).fetchTeachers();
    });
  }

  @override
  Widget build(BuildContext context) {
    final teacherProvider = Provider.of<TeacherProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Teachers'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const TeacherFormScreen()),
              );
            },
          ),
        ],
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
                : teacherProvider.teachers.isEmpty
                    ? const Text('No teachers available.')
                    : ListView.builder(
                        itemCount: teacherProvider.teachers.length,
                        itemBuilder: (context, index) {
                          final teacher = teacherProvider.teachers[index];
                          return Card(
                            margin: const EdgeInsets.all(8.0),
                            child: ListTile(
                              title: Text(
                                'Name: ${teacher.fullName ?? teacher.usuario.nombre}',
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Specialization: ${teacher.specialization ?? "N/A"}'),
                                  Text('Email: ${teacher.usuario.email}'),
                                ],
                              ),
                              onTap: () {
                                GoRouter.of(context).go('/teachers/${teacher.id}');
                              },
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}