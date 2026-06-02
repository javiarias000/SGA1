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

      // Guardar datos del usuario si el backend los retorna junto al token
      if (data.containsKey('rol')) {
        await prefs.setString('userRole', data['rol']?.toString() ?? 'ESTUDIANTE');
      }
      if (data.containsKey('nombre')) {
        await prefs.setString('userName', data['nombre']?.toString() ?? '');
      }
      if (data.containsKey('email')) {
        await prefs.setString('userEmail', data['email']?.toString() ?? '');
      }
      if (data.containsKey('is_staff')) {
        await prefs.setBool('isStaff', data['is_staff'] == true);
      }
      if (data.containsKey('student_id') && data['student_id'] != null) {
        await prefs.setInt('studentId', data['student_id'] as int);
      }

      return true;
    } catch (e) {
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
