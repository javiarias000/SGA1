import 'package:flutter/material.dart';
import 'package:mobile_app/services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService;
  bool _isLoggedIn = false;
  bool _isLoading = false;
  String? _authToken;
  String? _userRole; // New: store user role

  String? get authToken => _authToken;
  String? get userRole => _userRole; // Public getter for role

  AuthProvider(this._authService) {
    _checkLoginStatus();
  }

  bool get isLoggedIn => _isLoggedIn;
  bool get isLoading => _isLoading;

  Future<void> _checkLoginStatus() async {
    _isLoading = true;
    notifyListeners();
    _authToken = await _authService.getAuthToken();
    _isLoggedIn = _authToken != null && _authToken!.isNotEmpty;

    if (_isLoggedIn) {
      // We might need a dedicated endpoint to fetch the current user's role
      // For now, we'll assume the token check is enough and role is fetched during login
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final success = await _authService.login(username, password);
      if (success) {
        _authToken = await _authService.getAuthToken();
        _isLoggedIn = true;
        // In a real scenario, the backend should return the role with the token.
        // Since AuthService.login only returns bool, we'll simulate a role fetch or store it.
        _userRole = 'DOCENTE'; // Simulated: Should be fetched from backend
      } else {
        _authToken = null;
        _isLoggedIn = false;
        _userRole = null;
      }
    } catch (e) {
      print('Login failed in AuthProvider: $e');
      _isLoggedIn = false;
      _authToken = null;
      _userRole = null;
    }
    _isLoading = false;
    notifyListeners();
    return _isLoggedIn;
  }

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();
    await _authService.logout();
    _isLoggedIn = false;
    _authToken = null;
    _userRole = null;
    _isLoading = false;
    notifyListeners();
  }
}