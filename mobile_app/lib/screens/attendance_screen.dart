import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/providers/attendance_provider.dart';

class AttendanceScreen extends StatefulWidget {
  final int studentId;

  const AttendanceScreen({super.key, required this.studentId});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AttendanceProvider>(context, listen: false).fetchAttendance(widget.studentId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final attendanceProvider = Provider.of<AttendanceProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Attendance')),
      body: Center(
        child: attendanceProvider.isLoading
            ? const CircularProgressIndicator()
            : attendanceProvider.errorMessage.isNotEmpty
                ? Text(
                    attendanceProvider.errorMessage,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  )
                : attendanceProvider.attendanceRecords.isEmpty
                    ? const Text('No attendance records found.')
                    : ListView.builder(
                        itemCount: attendanceProvider.attendanceRecords.length,
                        itemBuilder: (context, index) {
                          final record = attendanceProvider.attendanceRecords[index];
                          return ListTile(
                            title: Text('Date: ${record['fecha']}'),
                            subtitle: Text('Status: ${record['estado']}'),
                            trailing: Text(record['observacion'] ?? 'No notes'),
                          );
                        },
                      ),
      ),
    );
  }
}
