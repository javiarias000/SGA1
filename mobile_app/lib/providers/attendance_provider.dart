import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/providers/auth_provider.dart';

class AttendanceProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider;
  List<dynamic> _attendanceRecords = [];
  bool _isLoading = false;
  String _errorMessage = '';

  AttendanceProvider(this._apiService, this._authProvider);

  List<dynamic> get attendanceRecords => _attendanceRecords;
  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;

  Future<void> fetchAttendance(int studentId) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');
      _attendanceRecords = await _apiService.fetchAttendance(studentId, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching attendance: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> markAttendance(Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');
      await _apiService.markAttendance(data, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error marking attendance: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
