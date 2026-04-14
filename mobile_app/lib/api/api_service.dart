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

  // Private helper for authenticated POST/PUT/PATCH requests
  Future<dynamic> _performWriteRequest(String method, String endpoint, dynamic data, {String? authToken}) async {
    final Map<String, String> headers = {
      'Content-Type': 'application/json; charset=UTF-8',
    };
    if (authToken != null && authToken.isNotEmpty) {
      headers['Authorization'] = 'Token $authToken';
    }

    final response = await http.send(
      http.Request(method, Uri.parse('$_baseUrl/$endpoint'))
        ..headers.addAll(headers)
        ..body = jsonEncode(data),
    );

    final responseBody = await response.stream.bytesToString();
    final statusCode = response.statusCode;

    if (statusCode >= 200 && statusCode < 300) {
      return json.decode(utf8.decode(response.bodyBytes));
    } else if (statusCode == 401) {
      throw UnauthorizedException('Session expired or token is invalid.');
    } else {
      throw Exception('Failed to $method data to $endpoint. Status: $statusCode, Body: $responseBody');
    }
  }

  // Private helper for authenticated DELETE requests
  Future<bool> _performDeleteRequest(String endpoint, {String? authToken}) async {
    final Map<String, String> headers = {
      'Content-Type': 'application/json; charset=UTF-8',
    };
    if (authToken != null && authToken.isNotEmpty) {
      headers['Authorization'] = 'Token $authToken';
    }

    final response = await http.delete(
      Uri.parse('$_baseUrl/$endpoint'),
      headers: headers,
    );

    if (response.statusCode == 204 || response.statusCode == 200) {
      return true;
    } else if (response.statusCode == 401) {
      throw UnauthorizedException('Session expired or token is invalid.');
    } else {
      throw Exception('Failed to delete data from $endpoint. Status: ${response.statusCode}, Body: ${response.body}');
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

  // --- CRUD Operations for Students ---

  Future<Student> createStudent(Map<String, dynamic> data, {String? authToken}) async {
    final dynamic result = await _performWriteRequest('POST', 'students/api/v1/students/', data, authToken: authToken);
    return Student.fromJson(result);
  }

  Future<Student> updateStudent(int studentId, Map<String, dynamic> data, {String? authToken}) async {
    final dynamic result = await _performWriteRequest('PATCH', 'students/api/v1/students/$studentId/', data, authToken: authToken);
    return Student.fromJson(result);
  }

  Future<bool> deleteStudent(int studentId, {String? authToken}) async {
    return await _performDeleteRequest('students/api/v1/students/$studentId/', authToken: authToken);
  }

  // --- CRUD Operations for Teachers ---

  Future<Teacher> createTeacher(Map<String, dynamic> data, {String? authToken}) async {
    final dynamic result = await _performWriteRequest('POST', 'teachers/api/v1/teachers/', data, authToken: authToken);
    return Teacher.fromJson(result);
  }

  Future<Teacher> updateTeacher(int teacherId, Map<String, dynamic> data, {String? authToken}) async {
    final dynamic result = await _performWriteRequest('PATCH', 'teachers/api/v1/teachers/$teacherId/', data, authToken: authToken);
    return Teacher.fromJson(result);
  }

  Future<bool> deleteTeacher(int teacherId, {String? authToken}) async {
    return await _performDeleteRequest('teachers/api/v1/teachers/$teacherId/', authToken: authToken);
  }

  // --- CRUD Operations for Subjects ---

  Future<Subject> createSubject(Map<String, dynamic> data, {String? authToken}) async {
    final dynamic result = await _performWriteRequest('POST', 'classes/api/v1/subjects/', data, authToken: authToken);
    return Subject.fromJson(result);
  }

  Future<Subject> updateSubject(int subjectId, Map<String, dynamic> data, {String? authToken}) async {
    final dynamic result = await _performWriteRequest('PATCH', 'classes/api/v1/subjects/$subjectId/', data, authToken: authToken);
    return Subject.fromJson(result);
  }

  Future<bool> deleteSubject(int subjectId, {String? authToken}) async {
    return await _performDeleteRequest('classes/api/v1/subjects/$subjectId/', authToken: authToken);
  }

  // --- Grading Operations ---

  Future<dynamic> fetchStudentGrades(int studentId, {String subject, String parcial, String quimestre, String? authToken}) async {
    String endpoint = 'teachers/obtener_calificaciones_estudiante/$studentId/';
    String query = '?subject=$subject&parcial=$parcial&quimestre=$quimestre';
    return await _performGetRequest(endpoint + query, authToken: authToken);
  }

  Future<dynamic> saveGrade({required int studentId, required String subject, required String parcial, required int tipoAporteId, required double calificacion, String? authToken}) async {
    final data = {
      'student_id': studentId,
      'subject': subject,
      'parcial': parcial,
      'tipo_aporte_id': tipoAporteId,
      'calificacion': calificacion,
    };
    return await _performWriteRequest('POST', 'teachers/guardar_calificacion_parcial/', data, authToken: authToken);
  }

  // --- Attendance Operations ---

  Future<dynamic> markAttendance(Map<String, dynamic> data, {String? authToken}) async {
    // Based on backend: teachers/views.py handles this via POST
    return await _performWriteRequest('POST', 'teachers/mark_attendance/', data, authToken: authToken);
  }

  Future<List<dynamic>> fetchAttendance(int studentId, {String? authToken}) async {
    return await _performGetRequest('api/attendance/?student=$studentId', authToken: authToken);
  }
}