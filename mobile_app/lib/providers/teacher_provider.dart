import 'package:flutter/material.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/models/teacher.dart';
import 'package:mobile_app/providers/auth_provider.dart';

class TeacherProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider; // Use AuthProvider
  List<Teacher> _teachers = [];
  Teacher? _selectedTeacher;
  String _errorMessage = '';
  bool _isLoading = false;

  TeacherProvider(this._apiService, this._authProvider);

  List<Teacher> get teachers => _teachers;
  Teacher? get selectedTeacher => _selectedTeacher;
  String get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;

  Future<void> fetchTeachers() async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _teachers = await _apiService.fetchTeachers(authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching teachers: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchTeacherDetail(int teacherId) async {
    _isLoading = true;
    _errorMessage = '';
    _selectedTeacher = null;
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _selectedTeacher = await _apiService.fetchTeacherDetail(teacherId, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching teacher detail: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> createTeacher(Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) throw Exception('User not authenticated.');

      final newTeacher = await _apiService.createTeacher(data, authToken: authToken);
      _teachers.add(newTeacher);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error creating teacher: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> updateTeacher(int teacherId, Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) throw Exception('User not authenticated.');

      final updatedTeacher = await _apiService.updateTeacher(teacherId, data, authToken: authToken);

      final index = _teachers.indexWhere((t) => t.id == teacherId);
      if (index != -1) {
        _teachers[index] = updatedTeacher;
      }
      if (_selectedTeacher?.id == teacherId) {
        _selectedTeacher = updatedTeacher;
      }
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error updating teacher: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> deleteTeacher(int teacherId) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) throw Exception('User not authenticated.');

      await _apiService.deleteTeacher(teacherId, authToken: authToken);
      _teachers.removeWhere((t) => t.id == teacherId);
      if (_selectedTeacher?.id == teacherId) {
        _selectedTeacher = null;
      }
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error deleting teacher: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearSelection() {
    _selectedTeacher = null;
    _errorMessage = '';
    notifyListeners();
  }
}