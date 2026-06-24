import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_service.dart';

class AuthService {
  final ApiService _apiService;

  AuthService(this._apiService);

  Future<bool> login(String username, String password) async {
    try {
      final data = await _apiService.login(username, password);
      final token = data['token']?.toString() ?? '';
      if (token.isEmpty) return false;

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('authToken', token);
      await prefs.setString('userRole', data['rol']?.toString() ?? 'ESTUDIANTE');
      await prefs.setString('userName', data['nombre']?.toString() ?? '');
      await prefs.setString('userEmail', data['email']?.toString() ?? '');
      await prefs.setBool('isStaff', data['is_staff'] == true);

      // student_id viene como num en Flutter web (JS) — usar toInt() para ser seguro
      final rawId = data['student_id'];
      if (rawId != null) {
        await prefs.setInt('studentId', (rawId as num).toInt());
      } else {
        await prefs.remove('studentId');
      }

      return true;
    } catch (e, st) {
      // ignore: avoid_print
      print('[AuthService.login] ERROR: $e\n$st');
      return false;
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  Future<String?> getAuthToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('authToken');
  }

  Future<bool> isAuthenticated() async {
    final token = await getAuthToken();
    return token != null && token.isNotEmpty;
  }
}
