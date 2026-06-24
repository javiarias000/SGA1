import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_service.dart';
import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService;

  bool _isLoggedIn = false;
  bool _isLoading = false;
  String? _authToken;
  String? _userRole;
  String? _userName;
  String? _userEmail;
  int? _studentId;
  bool _isStaff = false;

  AuthProvider(this._authService) {
    _checkLoginStatus();
  }

  bool get isLoggedIn => _isLoggedIn;
  bool get isLoading => _isLoading;
  String? get authToken => _authToken;
  String? get token => _authToken; // alias
  String? get userRole => _userRole;
  String? get userName => _userName;
  String? get userEmail => _userEmail;
  int? get studentId => _studentId;
  int? get userId => _studentId; // alias (used for teacher context too)
  bool get isStaff => _isStaff;

  Future<void> _checkLoginStatus() async {
    _isLoading = true;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    _authToken = prefs.getString('authToken');
    _userRole = prefs.getString('userRole');
    _userName = prefs.getString('userName');
    _userEmail = prefs.getString('userEmail');
    _studentId = prefs.getInt('studentId');
    _isStaff = prefs.getBool('isStaff') ?? false;
    _isLoggedIn = _authToken != null && _authToken!.isNotEmpty;
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
        await _fetchUserInfo();
      } else {
        _clear();
      }
    } catch (e) {
      _clear();
    }
    _isLoading = false;
    notifyListeners();
    return _isLoggedIn;
  }

  Future<void> _fetchUserInfo() async {
    if (_authToken == null) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      // Try fetching from /api/me/ endpoint
      // If not available, decode from stored prefs
      _userRole = prefs.getString('userRole') ?? 'ESTUDIANTE';
      _userName = prefs.getString('userName') ?? '';
      _userEmail = prefs.getString('userEmail') ?? '';
      _studentId = prefs.getInt('studentId');
      _isStaff = prefs.getBool('isStaff') ?? false;
    } catch (_) {}
  }

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();
    await _authService.logout();
    _clear();
    _isLoading = false;
    notifyListeners();
  }

  void _clear() {
    _isLoggedIn = false;
    _authToken = null;
    _userRole = null;
    _userName = null;
    _userEmail = null;
    _studentId = null;
    _isStaff = false;
  }
}
