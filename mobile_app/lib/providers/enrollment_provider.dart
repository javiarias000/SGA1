import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/providers/auth_provider.dart';
import 'package:mobile_app/models/clase.dart';

class EnrollmentProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider;
  List<dynamic> _enrollments = [];
  bool _isLoading = false;
  String _errorMessage = '';

  EnrollmentProvider(this._apiService, this._authProvider);

  List<dynamic> get enrollments => _enrollments;
  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;

  Future<void> fetchEnrollments(int studentId) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');
      _enrollments = await _apiService.fetchEnrollments(studentId, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching enrollments: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> enrollStudent(Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');
      await _apiService.createEnrollment(data, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error enrolling student: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
