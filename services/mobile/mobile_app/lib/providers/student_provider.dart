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
      final authToken = _authProvider.authToken;
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
      final authToken = _authProvider.authToken;
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

  Future<void> createStudent(Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');

      final newStudent = await _apiService.createStudent(data, authToken: authToken);
      _students.add(newStudent);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error creating student: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> updateStudent(int studentId, Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');

      final updatedStudent = await _apiService.updateStudent(studentId, data, authToken: authToken);

      final index = _students.indexWhere((s) => s.id == studentId);
      if (index != -1) {
        _students[index] = updatedStudent;
      }
      if (_selectedStudent?.id == studentId) {
        _selectedStudent = updatedStudent;
      }
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error updating student: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> deleteStudent(int studentId) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');

      await _apiService.deleteStudent(studentId, authToken: authToken);
      _students.removeWhere((s) => s.id == studentId);
      if (_selectedStudent?.id == studentId) {
        _selectedStudent = null;
      }
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error deleting student: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearSelection() {
    _selectedStudent = null;
    notifyListeners();
  }
}