import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'api_exceptions.dart';
import '../core/constants.dart';
import '../models/horario.dart';
import '../models/student.dart';
import '../models/teacher.dart';
import '../models/clase.dart';
import '../models/subject.dart';

class ApiService {
  final String _baseUrl = ApiConfig.baseUrl;

  Map<String, String> _headers({String? authToken, bool json = true}) {
    return {
      if (json) 'Content-Type': 'application/json; charset=UTF-8',
      if (authToken != null && authToken.isNotEmpty)
        'Authorization': 'Token $authToken',
    };
  }

  Future<dynamic> _get(String endpoint, {String? authToken, Map<String, String>? query}) async {
    Uri uri = Uri.parse('$_baseUrl/$endpoint');
    if (query != null) uri = uri.replace(queryParameters: query);
    final response = await http.get(uri, headers: _headers(authToken: authToken));
    return _handleResponse(response, endpoint);
  }

  Future<dynamic> _post(String endpoint, dynamic data, {String? authToken}) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/$endpoint'),
      headers: _headers(authToken: authToken),
      body: jsonEncode(data),
    );
    return _handleResponse(response, endpoint);
  }

  Future<dynamic> _patch(String endpoint, dynamic data, {String? authToken}) async {
    final response = await http.patch(
      Uri.parse('$_baseUrl/$endpoint'),
      headers: _headers(authToken: authToken),
      body: jsonEncode(data),
    );
    return _handleResponse(response, endpoint);
  }

  Future<bool> _delete(String endpoint, {String? authToken}) async {
    final response = await http.delete(
      Uri.parse('$_baseUrl/$endpoint'),
      headers: _headers(authToken: authToken),
    );
    if (response.statusCode == 204 || response.statusCode == 200) return true;
    if (response.statusCode == 401) throw UnauthorizedException('Token inválido.');
    throw Exception('DELETE $endpoint falló: ${response.statusCode}');
  }

  dynamic _handleResponse(http.Response response, String endpoint) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return json.decode(utf8.decode(response.bodyBytes));
    }
    if (response.statusCode == 401) throw UnauthorizedException('Sesión expirada.');
    throw Exception('$endpoint → ${response.statusCode}: ${response.body}');
  }

  // ─── AUTH ──────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/token/auth/'),
      headers: {'Content-Type': 'application/json; charset=UTF-8'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Login fallido: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> fetchCurrentUser({required String authToken}) async {
    return await _get('api/me/', authToken: authToken);
  }

  // ─── HORARIOS ─────────────────────────────────────────────────────────────

  Future<List<Horario>> fetchHorarios({String? authToken}) async {
    final body = await _get('academia/api/v1/horarios/', authToken: authToken);
    return (body as List).map((e) => Horario.fromJson(e)).toList();
  }

  Future<Horario> fetchHorarioDetail(int id, {String? authToken}) async {
    final body = await _get('academia/api/v1/horarios/$id/', authToken: authToken);
    return Horario.fromJson(body);
  }

  // ─── STUDENTS ─────────────────────────────────────────────────────────────

  Future<List<Student>> fetchStudents({String? authToken}) async {
    final body = await _get('students/api/v1/students/', authToken: authToken);
    return (body as List).map((e) => Student.fromJson(e)).toList();
  }

  Future<Student> fetchStudentDetail(int id, {String? authToken}) async {
    final body = await _get('students/api/v1/students/$id/', authToken: authToken);
    return Student.fromJson(body);
  }

  Future<Student> createStudent(Map<String, dynamic> data, {String? authToken}) async {
    return Student.fromJson(await _post('students/api/v1/students/', data, authToken: authToken));
  }

  Future<Student> updateStudent(int id, Map<String, dynamic> data, {String? authToken}) async {
    return Student.fromJson(await _patch('students/api/v1/students/$id/', data, authToken: authToken));
  }

  Future<bool> deleteStudent(int id, {String? authToken}) async =>
      _delete('students/api/v1/students/$id/', authToken: authToken);

  // ─── TEACHERS ─────────────────────────────────────────────────────────────

  Future<List<Teacher>> fetchTeachers({String? authToken}) async {
    final body = await _get('teachers/api/v1/teachers/', authToken: authToken);
    return (body as List).map((e) => Teacher.fromJson(e)).toList();
  }

  Future<Teacher> fetchTeacherDetail(int id, {String? authToken}) async {
    final body = await _get('teachers/api/v1/teachers/$id/', authToken: authToken);
    return Teacher.fromJson(body);
  }

  Future<Teacher> createTeacher(Map<String, dynamic> data, {String? authToken}) async {
    return Teacher.fromJson(await _post('teachers/api/v1/teachers/', data, authToken: authToken));
  }

  Future<Teacher> updateTeacher(int id, Map<String, dynamic> data, {String? authToken}) async {
    return Teacher.fromJson(await _patch('teachers/api/v1/teachers/$id/', data, authToken: authToken));
  }

  Future<bool> deleteTeacher(int id, {String? authToken}) async =>
      _delete('teachers/api/v1/teachers/$id/', authToken: authToken);

  // ─── SUBJECTS ─────────────────────────────────────────────────────────────

  Future<Subject> fetchSubjectDetail(int id, {String? authToken}) async {
    final body = await _get('classes/api/v1/subjects/$id/', authToken: authToken);
    return Subject.fromJson(body);
  }

  Future<Subject> createSubject(Map<String, dynamic> data, {String? authToken}) async {
    return Subject.fromJson(await _post('classes/api/v1/subjects/', data, authToken: authToken));
  }

  Future<Subject> updateSubject(int id, Map<String, dynamic> data, {String? authToken}) async {
    return Subject.fromJson(await _patch('classes/api/v1/subjects/$id/', data, authToken: authToken));
  }

  Future<bool> deleteSubject(int id, {String? authToken}) async =>
      _delete('classes/api/v1/subjects/$id/', authToken: authToken);

  // ─── CLASES ───────────────────────────────────────────────────────────────

  Future<List<Clase>> fetchClases({String? authToken}) async {
    final body = await _get('classes/api/v1/clases/', authToken: authToken);
    return (body as List).map((e) => Clase.fromJson(e)).toList();
  }

  // ─── TIPOS DE APORTE ──────────────────────────────────────────────────────

  Future<List<dynamic>> fetchTiposAporte({String? authToken}) async {
    return await _get('classes/api/v1/tipos-aportes/', authToken: authToken);
  }

  // ─── GRADES ───────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchStudentGrades(int studentId,
      {String? subject, String? parcial, String? quimestre, String? authToken}) async {
    return await _get(
      'classes/api/v1/calificaciones/',
      authToken: authToken,
      query: {
        'student': studentId.toString(),
        if (subject != null) 'subject': subject,
        if (parcial != null) 'parcial': parcial,
        if (quimestre != null) 'quimestre': quimestre,
      },
    );
  }

  Future<dynamic> saveGrade({
    required int studentId,
    required int subjectId,
    required String parcial,
    required String quimestre,
    required int tipoAporteId,
    required double calificacion,
    String? authToken,
  }) async {
    return _post('classes/api/v1/calificaciones/', {
      'student': studentId,
      'subject': subjectId,
      'parcial': parcial,
      'quimestre': quimestre,
      'tipo_aporte': tipoAporteId,
      'calificacion': calificacion,
    }, authToken: authToken);
  }

  // ─── ATTENDANCE ───────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchAttendance(int studentId, {String? authToken}) async {
    return await _get('classes/api/v1/asistencia/',
        authToken: authToken, query: {'student': studentId.toString()});
  }

  Future<dynamic> markAttendance(Map<String, dynamic> data, {String? authToken}) async {
    return _post('classes/api/v1/asistencia/', data, authToken: authToken);
  }

  Future<dynamic> updateAttendance(int id, Map<String, dynamic> data, {String? authToken}) async {
    return _patch('classes/api/v1/asistencia/$id/', data, authToken: authToken);
  }

  // ─── ENROLLMENTS ──────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchEnrollments(int studentId, {String? authToken}) async {
    return await _get('classes/api/v1/enrollments/',
        authToken: authToken, query: {'student': studentId.toString()});
  }

  Future<dynamic> createEnrollment(Map<String, dynamic> data, {String? authToken}) async {
    return _post('classes/api/v1/enrollments/', data, authToken: authToken);
  }

  // ─── MATRICULAS ───────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> crearMatricula(
    Map<String, dynamic> datos,
    Map<String, File> archivos, {
    String? authToken,
  }) async {
    final request = http.MultipartRequest(
        'POST', Uri.parse('$_baseUrl/matriculas/api/nueva/'));
    if (authToken != null) request.headers['Authorization'] = 'Token $authToken';

    datos.forEach((key, val) {
      request.fields[key] = val.toString();
    });
    for (final entry in archivos.entries) {
      request.files.add(await http.MultipartFile.fromPath(entry.key, entry.value.path));
    }
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    return _handleResponse(response, 'matriculas/api/nueva/');
  }

  Future<Map<String, dynamic>> seguimientoMatricula(String busqueda,
      {String? authToken}) async {
    return await _get('matriculas/api/seguimiento/',
        authToken: authToken, query: {'q': busqueda});
  }

  Future<List<dynamic>> fetchSolicitudesSecretaria({
    String? estado, String? busqueda, String? authToken,
  }) async {
    return await _get('matriculas/api/lista/',
        authToken: authToken,
        query: {
          if (estado != null && estado.isNotEmpty) 'estado': estado,
          if (busqueda != null && busqueda.isNotEmpty) 'q': busqueda,
        });
  }

  Future<Map<String, dynamic>> fetchSolicitudDetalle(int pk,
      {String? authToken}) async {
    return await _get('matriculas/api/$pk/', authToken: authToken);
  }

  Future<Map<String, dynamic>> actualizarSolicitud(
      int pk, Map<String, dynamic> data, {String? authToken}) async {
    return await _patch('matriculas/api/$pk/', data, authToken: authToken);
  }

  // ─── AGENTE IA ────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchAlertas({
    String? severidad, String? tipo, String? estado, String? authToken,
  }) async {
    return await _get('agente/api/alertas/', authToken: authToken, query: {
      if (severidad != null && severidad.isNotEmpty) 'severidad': severidad,
      if (tipo != null && tipo.isNotEmpty) 'tipo': tipo,
      if (estado != null && estado.isNotEmpty) 'estado': estado,
    });
  }

  Future<Map<String, dynamic>> fetchAlertaDetalle(int pk,
      {String? authToken}) async {
    return await _get('agente/api/alertas/$pk/', authToken: authToken);
  }

  Future<Map<String, dynamic>> actualizarEstadoAlerta(int pk, String estado,
      {String? authToken}) async {
    return await _patch('agente/api/alertas/$pk/', {'estado': estado},
        authToken: authToken);
  }

  Future<Map<String, dynamic>> analizarEstudiante(int studentId,
      {String? authToken}) async {
    return await _post('agente/api/analizar/$studentId/', {},
        authToken: authToken);
  }

  Future<Map<String, dynamic>> mejorarInforme(String texto,
      {int? activityId, String? authToken}) async {
    return await _post('agente/api/mejorar-informe/', {
      'texto_original': texto,
      if (activityId != null) 'activity_id': activityId,
    }, authToken: authToken);
  }

  // ─── ACTIVIDADES / REGISTRO ───────────────────────────────────────────────

  Future<List<dynamic>> fetchActividades({
    int? studentId, int? claseId, int? subjectId, String? authToken,
  }) async {
    return await _get('classes/api/v1/actividades/', authToken: authToken, query: {
      if (studentId != null) 'student': studentId.toString(),
      if (claseId != null) 'clase': claseId.toString(),
      if (subjectId != null) 'subject': subjectId.toString(),
    });
  }

  Future<dynamic> createActividad(Map<String, dynamic> data, {String? authToken}) async {
    return _post('classes/api/v1/actividades/', data, authToken: authToken);
  }

  Future<dynamic> updateActividad(int id, Map<String, dynamic> data, {String? authToken}) async {
    return _patch('classes/api/v1/actividades/$id/', data, authToken: authToken);
  }

  Future<bool> deleteActividad(int id, {String? authToken}) async =>
      _delete('classes/api/v1/actividades/$id/', authToken: authToken);

  // ─── DEBERES ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchDeberes({
    int? claseId, String? estado, int? teacherId, String? authToken,
  }) async {
    return await _get('classes/api/v1/deberes/', authToken: authToken, query: {
      if (claseId != null) 'clase': claseId.toString(),
      if (estado != null && estado.isNotEmpty) 'estado': estado,
      if (teacherId != null) 'teacher': teacherId.toString(),
    });
  }

  Future<dynamic> createDeber(Map<String, dynamic> data, {String? authToken}) async {
    return _post('classes/api/v1/deberes/', data, authToken: authToken);
  }

  Future<dynamic> updateDeber(int id, Map<String, dynamic> data, {String? authToken}) async {
    return _patch('classes/api/v1/deberes/$id/', data, authToken: authToken);
  }

  Future<bool> deleteDeber(int id, {String? authToken}) async =>
      _delete('classes/api/v1/deberes/$id/', authToken: authToken);

  Future<List<dynamic>> fetchEntregasDeber(int deberId, {String? authToken}) async {
    return await _get('classes/api/v1/deberes/$deberId/entregas/', authToken: authToken);
  }

  // ─── ENTREGAS DE DEBERES ──────────────────────────────────────────────────

  Future<List<dynamic>> fetchMisEntregas({int? estudianteId, String? authToken}) async {
    return await _get('classes/api/v1/entregas/', authToken: authToken, query: {
      if (estudianteId != null) 'estudiante': estudianteId.toString(),
    });
  }

  Future<dynamic> crearEntrega(Map<String, dynamic> data, {String? authToken}) async {
    return _post('classes/api/v1/entregas/', data, authToken: authToken);
  }

  Future<dynamic> calificarEntrega(int id, Map<String, dynamic> data, {String? authToken}) async {
    return _patch('classes/api/v1/entregas/$id/', data, authToken: authToken);
  }

  // ─── LIBRETA ─────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> fetchLibreta(int studentId, {String? authToken}) async {
    return await _get('teachers/api/v1/libreta/$studentId/', authToken: authToken);
  }

  // ─── NOTIFICACIONES ───────────────────────────────────────────────────────

  Future<Map<String, dynamic>> enviarNotificacionWhatsApp({
    required int studentId,
    required String tipo,
    String? authToken,
  }) async {
    if (tipo == 'grades') {
      return await _get(
        'teachers/informes/student/$studentId/whatsapp/grades/',
        authToken: authToken,
      );
    } else {
      return await _get(
        'teachers/informes/student/$studentId/whatsapp/attendance/',
        authToken: authToken,
      );
    }
  }

  Future<Map<String, dynamic>> enviarReporteEmail({
    required int studentId,
    String? authToken,
  }) async {
    return await _get(
      'teachers/informes/student/$studentId/email/',
      authToken: authToken,
    );
  }
}
