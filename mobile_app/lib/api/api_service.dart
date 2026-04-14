import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_exceptions.dart'; // Import custom exception
import '../models/horario.dart';
import '../models/student.dart';
import '../models/teacher.dart';
import '../models/clase.dart';
import '../models/subject.dart';

class ApiService {
  final String _baseUrl = 'http://127.0.0.1:8000';

  // Private helper for authenticated GET requests
  Future<dynamic> _performGetRequest(String endpoint, {String? authToken}) async {
    final Map<String, String> headers = {
      'Content-Type': 'application/json; charset=UTF-8',
    };
    if (authToken != null && authToken.isNotEmpty) {
      headers['Authorization'] = 'Token $authToken';
    }

    final response = await http.get(
      Uri.parse('$_baseUrl/$endpoint'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return json.decode(utf8.decode(response.bodyBytes));
    } else if (response.statusCode == 401) {
      throw UnauthorizedException('Session expired or token is invalid.');
    } else {
      throw Exception('Failed to load data from $endpoint. Status: ${response.statusCode}, Body: ${response.body}');
    }
  }

  Future<String> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/token/auth/'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['token'];
    } else {
      print('Login failed. Status: ${response.statusCode}, Error: ${response.body}');
      throw Exception('Failed to log in. Status: ${response.statusCode}, Error: ${response.body}');
    }
  }

  Future<List<Horario>> fetchHorarios({String? authToken}) async {
    try {
      final List<dynamic> body = await _performGetRequest('academia/api/v1/horarios/', authToken: authToken);
      return body.map((dynamic item) => Horario.fromJson(item)).toList();
    } catch (e) {
      throw Exception('Failed to connect to API for horarios: $e');
    }
  }

  Future<List<Student>> fetchStudents({String? authToken}) async {
    try {
      final List<dynamic> body = await _performGetRequest('students/api/v1/students/', authToken: authToken);
      return body.map((dynamic item) => Student.fromJson(item)).toList();
    } catch (e) {
      throw Exception('Failed to connect to API for students: $e');
    }
  }

  Future<List<Teacher>> fetchTeachers({String? authToken}) async {
    try {
      final List<dynamic> body = await _performGetRequest('teachers/api/v1/teachers/', authToken: authToken);
      return body.map((dynamic item) => Teacher.fromJson(item)).toList();
    } catch (e) {
      throw Exception('Failed to connect to API for teachers: $e');
    }
  }

  Future<List<Clase>> fetchClases({String? authToken}) async {
    try {
      final List<dynamic> body = await _performGetRequest('classes/api/v1/clases/', authToken: authToken);
      return body.map((dynamic item) => Clase.fromJson(item)).toList();
    } catch (e) {
      throw Exception('Failed to connect to API for clases: $e');
    }
  }

  Future<Student> fetchStudentDetail(int studentId, {String? authToken}) async {
    try {
      final Map<String, dynamic> body = await _performGetRequest('students/api/v1/students/$studentId/', authToken: authToken);
      return Student.fromJson(body);
    } catch (e) {
      throw Exception('Failed to connect to API for student detail: $e');
    }
  }

  Future<Teacher> fetchTeacherDetail(int teacherId, {String? authToken}) async {
    try {
      final Map<String, dynamic> body = await _performGetRequest('teachers/api/v1/teachers/$teacherId/', authToken: authToken);
      return Teacher.fromJson(body);
    } catch (e) {
      throw Exception('Failed to connect to API for teacher detail: $e');
    }
  }

  Future<Horario> fetchHorarioDetail(int horarioId, {String? authToken}) async {
    try {
      final Map<String, dynamic> body = await _performGetRequest('academia/api/v1/horarios/$horarioId/', authToken: authToken);
      return Horario.fromJson(body);
    } catch (e) {
      throw Exception('Failed to connect to API for horario detail: $e');
    }
  }
  
  Future<Subject> fetchSubjectDetail(int subjectId, {String? authToken}) async {
    try {
      final Map<String, dynamic> body = await _performGetRequest('classes/api/v1/subjects/$subjectId/', authToken: authToken);
      return Subject.fromJson(body);
    } catch (e) {
      throw Exception('Failed to connect to API for subject detail: $e');
    }
  }
}