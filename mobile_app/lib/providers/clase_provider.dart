import 'package:flutter/material.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/models/clase.dart';
import 'package:mobile_app/providers/auth_provider.dart';

class ClaseProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider; // Use AuthProvider
  List<Clase> _clases = [];
  String _errorMessage = '';
  bool _isLoading = false;

  ClaseProvider(this._apiService, this._authProvider);

  List<Clase> get clases => _clases;
  String get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;

  Future<void> fetchClases() async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = _authProvider.authToken;
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _clases = await _apiService.fetchClases(authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching clases: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}