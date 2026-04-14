import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/subject_provider.dart';
import 'package:mobile_app/screens/subject_form_screen.dart';

class SubjectDetailScreen extends StatefulWidget {
  final int subjectId;

  const SubjectDetailScreen({Key? key, required this.subjectId}) : super(key: key);

  @override
  _SubjectDetailScreenState createState() => _SubjectDetailScreenState();
}

class _SubjectDetailScreenState extends State<SubjectDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<SubjectProvider>(context, listen: false).selectSubject(widget.subjectId);
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<SubjectProvider>(context, listen: false).clearSelection();
    });
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Consumer<SubjectProvider>(
          builder: (context, provider, child) {
            return Text(provider.selectedSubject?.name ?? 'Subject Detail');
          },
        ),
        actions: [
          if (Provider.of<SubjectProvider>(context).selectedSubject != null)
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => SubjectFormScreen(
                      subject: Provider.of<SubjectProvider>(context, listen: false).selectedSubject,
                    ),
                  ),
                );
              },
            ),
          if (Provider.of<SubjectProvider>(context).selectedSubject != null)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _confirmDelete(context),
            ),
        ],
      ),
      body: Consumer<SubjectProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return Center(child: CircularProgressIndicator());
          }

          if (provider.errorMessage.isNotEmpty) {
            return Center(child: Text('Error: ${provider.errorMessage}'));
          }

          if (provider.selectedSubject == null) {
            return Center(child: Text('No subject selected or found.'));
          }

          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Teachers for this Subject:',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                SizedBox(height: 10),
                Expanded(
                  child: provider.associatedTeachers.isEmpty
                      ? Text('No teachers found for this subject.')
                      : ListView.builder(
                          itemCount: provider.associatedTeachers.length,
                          itemBuilder: (context, index) {
                            final teacher = provider.associatedTeachers[index];
                            return Card(
                              child: ListTile(
                                leading: teacher.photo != null
                                    ? CircleAvatar(
                                        backgroundImage: NetworkImage(teacher.photo!),
                                      )
                                    : CircleAvatar(child: Icon(Icons.person)),
                                title: Text(teacher.fullName ?? 'No Name'),
                                subtitle: Text(teacher.specialization ?? 'No Specialization'),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _confirmDelete(BuildContext context) {
    final provider = Provider.of<SubjectProvider>(context, listen: false);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Subject'),
        content: const Text('Are you sure you want to delete this subject?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              await provider.deleteSubject(provider.selectedSubject!.id);
              if (context.mounted) {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Subject deleted successfully')),
                );
                provider.clearSelection();
                Navigator.pop(context);
              }
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}
