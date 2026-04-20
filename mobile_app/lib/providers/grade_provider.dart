import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/providers/auth_provider.dart';

class GradeProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider;
  Map<String, dynamic> _currentGrades = {};
  bool _isLoading = false;
  String _errorMessage = '';

  GradeProvider(this._apiService, this._authProvider);

  Map<String, dynamic> get currentGrades => _currentGrades;
  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;

  Future<void> fetchGrades(int studentId, String subject, String parcial, String quimestre) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');
      _currentGrades = await _apiService.fetchStudentGrades(
        studentId,
        subject: subject,
        parcial: parcial,
        quimestre: quimestre,
        authToken: authToken
      );
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching grades: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> saveGrade({
    required int studentId,
    required String subject,
    required String parcial,
    required int tipoAporteId,
    required double calificacion
  }) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) throw Exception('User not authenticated.');
      await _apiService.saveGrade(
        studentId: studentId,
        subject: subject,
        parcial: parcial,
        tipoAporteId: tipoAporteId,
        calificacion: calificacion,
        authToken: authToken,
      );
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error saving grade: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
