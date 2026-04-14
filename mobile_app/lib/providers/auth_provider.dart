import 'package:flutter/material.dart';
import 'package:mobile_app/services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService;
  bool _isLoggedIn = false;
  bool _isLoading = false;
  String? _authToken; // Cache the token

  String? get authToken => _authToken; // Public getter for the token

  AuthProvider(this._authService) {
    _checkLoginStatus();
  }

  bool get isLoggedIn => _isLoggedIn;
  bool get isLoading => _isLoading;

  Future<void> _checkLoginStatus() async {
    _isLoading = true;
    notifyListeners();
    _authToken = await _authService.getAuthToken(); // Get token during check
    _isLoggedIn = _authToken != null && _authToken!.isNotEmpty;
    _isLoading = false;
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final success = await _authService.login(username, password); // AuthService.login returns bool
      if (success) {
        _authToken = await _authService.getAuthToken(); // Get the actual token after successful login
        _isLoggedIn = true;
      } else {
        _authToken = null;
        _isLoggedIn = false;
      }
    } catch (e) {
      print('Login failed in AuthProvider: $e');
      _isLoggedIn = false;
      _authToken = null;
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
    _authToken = null; // Clear cached token
    _isLoading = false;
    notifyListeners();
  }
}