import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../api/api_exceptions.dart';
import 'auth_provider.dart';

class AttendanceProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider;
  List<dynamic> _records = [];
  bool _isLoading = false;
  String _errorMessage = '';

  AttendanceProvider(this._apiService, this._authProvider);

  List<dynamic> get records => _records;
  List<dynamic> get attendanceRecords => _records; // compat alias
  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;

  int get totalClases => _records.length;
  int get presentes => _records.where((r) => r['estado']?.toString().toLowerCase() == 'presente').length;
  int get ausentes => _records.where((r) => r['estado']?.toString().toLowerCase() == 'ausente').length;
  int get tardanzas => _records.where((r) => r['estado']?.toString().toLowerCase() == 'tardanza').length;

  Future<void> fetchAttendance(int studentId) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();
    try {
      final token = _authProvider.authToken;
      if (token == null) throw Exception('No autenticado.');
      _records = await _apiService.fetchAttendance(studentId, authToken: token);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> markAttendance(Map<String, dynamic> data) async {
    final token = _authProvider.authToken;
    if (token == null) throw Exception('No autenticado.');
    await _apiService.markAttendance(data, authToken: token);
  }
}
