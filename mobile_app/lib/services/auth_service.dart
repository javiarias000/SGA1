import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_service.dart';

class AuthService {
  final ApiService _apiService;
  static const String _authTokenKey = 'authToken';

  AuthService(this._apiService);

  Future<bool> login(String username, String password) async {
    try {
      final token = await _apiService.login(username, password);
      if (token.isNotEmpty) {
        await _saveAuthToken(token);
        return true;
      }
      return false;
    } catch (e) {
      print('Login failed: $e'); // For debugging
      return false;
    }
  }

  Future<void> logout() async {
    await _deleteAuthToken();
  }

  Future<String?> getAuthToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_authTokenKey);
  }

  Future<void> _saveAuthToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_authTokenKey, token);
  }

  Future<void> _deleteAuthToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_authTokenKey);
  }

  Future<bool> isAuthenticated() async {
    final token = await getAuthToken();
    return token != null && token.isNotEmpty;
  }
}