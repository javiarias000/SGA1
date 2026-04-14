import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart'; // Import GoRouter
import 'package:mobile_app/providers/subject_provider.dart'; // Import SubjectProvider

class SubjectsListScreen extends StatefulWidget {
  const SubjectsListScreen({super.key});

  @override
  State<SubjectsListScreen> createState() => _SubjectsListScreenState();
}

class _SubjectsListScreenState extends State<SubjectsListScreen> {
  @override
  void initState() {
    super.initState();
    // No need to fetch directly here, SubjectProvider listens to ClaseProvider
  }

  @override
  Widget build(BuildContext context) {
    final subjectProvider = Provider.of<SubjectProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Subjects'),
      ),
      body: Center(
        child: subjectProvider.isLoading
            ? const CircularProgressIndicator()
            : subjectProvider.errorMessage.isNotEmpty
                ? Text(
                    subjectProvider.errorMessage,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  )
                : subjectProvider.subjects.isEmpty
                    ? const Text('No subjects available.')
                    : ListView.builder(
                        itemCount: subjectProvider.subjects.length,
                        itemBuilder: (context, index) {
                          final subject = subjectProvider.subjects[index];
                          return Card(
                            margin: const EdgeInsets.all(8.0),
                            child: InkWell( // Use InkWell for tap detection
                              onTap: () {
                                GoRouter.of(context).go('/subjects/${subject.id}');
                              },
                              child: Padding(
                                padding: const EdgeInsets.all(16.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Name: ${subject.name}',
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    Text('Type: ${subject.tipoMateria}'),
                                    Text('Description: ${subject.description}'),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}