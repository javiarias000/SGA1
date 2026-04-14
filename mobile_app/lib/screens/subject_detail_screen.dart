import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/subject_provider.dart';

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
    // Fetch details when the screen is first built
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<SubjectProvider>(context, listen: false).selectSubject(widget.subjectId);
    });
  }

  @override
  void dispose() {
    // Clear the selection when the screen is disposed
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
                  style: Theme.of(context).textTheme.headline6,
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
}
