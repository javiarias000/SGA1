import 'package:flutter/material.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/models/student.dart';
import 'package:mobile_app/providers/auth_provider.dart';

class StudentProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider; // Use AuthProvider
  List<Student> _students = [];
  Student? _selectedStudent;
  String _errorMessage = '';
  bool _isLoading = false;

  StudentProvider(this._apiService, this._authProvider);

  List<Student> get students => _students;
  Student? get selectedStudent => _selectedStudent;
  String get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;

  Future<void> fetchStudents() async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _students = await _apiService.fetchStudents(authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching students: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchStudentDetail(int studentId) async {
    _isLoading = true;
    _errorMessage = '';
    _selectedStudent = null;
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _selectedStudent = await _apiService.fetchStudentDetail(studentId, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching student detail: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}