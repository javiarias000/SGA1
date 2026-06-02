import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../api/api_exceptions.dart';
import 'auth_provider.dart';

class GradeProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider;
  List<dynamic> _gradesList = [];
  bool _isLoading = false;
  String _errorMessage = '';

  GradeProvider(this._apiService, this._authProvider);

  List<dynamic> get gradesList => _gradesList;
  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;

  double? get promedioGeneral {
    final vals = _gradesList
        .map((g) => _parseNota(g['calificacion'] ?? g['nota']))
        .whereType<double>()
        .toList();
    if (vals.isEmpty) return null;
    return vals.reduce((a, b) => a + b) / vals.length;
  }

  double? _parseNota(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  Future<void> fetchGrades(int studentId,
      {String? subject, String? parcial, String? quimestre}) async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();
    try {
      final token = _authProvider.authToken;
      if (token == null) throw Exception('No autenticado.');
      final result = await _apiService.fetchStudentGrades(
        studentId,
        subject: subject,
        parcial: parcial,
        quimestre: quimestre,
        authToken: token,
      );
      if (result is List) {
        _gradesList = result;
      } else if (result is Map) {
        final m = result as Map<String, dynamic>;
        _gradesList = (m['calificaciones'] ?? m['results'] ?? []) as List;
      } else {
        _gradesList = [];
      }
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> saveGrade({
    required int studentId,
    required int subjectId,
    required String parcial,
    required String quimestre,
    required int tipoAporteId,
    required double calificacion,
  }) async {
    final token = _authProvider.authToken;
    if (token == null) throw Exception('No autenticado.');
    await _apiService.saveGrade(
      studentId: studentId,
      subjectId: subjectId,
      parcial: parcial,
      quimestre: quimestre,
      tipoAporteId: tipoAporteId,
      calificacion: calificacion,
      authToken: token,
    );
  }

  String? get token => _authProvider.authToken;
}
