import 'package:flutter/material.dart';
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/api/api_exceptions.dart';
import 'package:mobile_app/models/horario.dart';
import 'package:mobile_app/providers/auth_provider.dart';

class HorarioProvider extends ChangeNotifier {
  final ApiService _apiService;
  final AuthProvider _authProvider; // Use AuthProvider
  List<Horario> _horarios = [];
  Horario? _selectedHorario;
  String _errorMessage = '';
  bool _isLoading = false;

  HorarioProvider(this._apiService, this._authProvider);

  List<Horario> get horarios => _horarios;
  Horario? get selectedHorario => _selectedHorario;
  String get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;

  Future<void> fetchHorarios() async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _horarios = await _apiService.fetchHorarios(authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching horarios: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchHorarioDetail(int horarioId) async {
    _isLoading = true;
    _errorMessage = '';
    _selectedHorario = null;
    notifyListeners();

    try {
      final authToken = await _authProvider.getAuthToken();
      if (authToken == null) {
        throw Exception('User not authenticated.');
      }
      _selectedHorario = await _apiService.fetchHorarioDetail(horarioId, authToken: authToken);
    } on UnauthorizedException {
      await _authProvider.logout();
    } catch (e) {
      _errorMessage = 'Error fetching horario detail: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}