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
}