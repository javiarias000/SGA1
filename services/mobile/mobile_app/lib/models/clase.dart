import 'user.dart';
import 'subject.dart';
import 'grade_level.dart';

class Clase {
  final int id;
  final String name;
  final Subject? subject; // Nested Subject object
  final String cicloLectivo;
  final String paralelo;
  final User? docenteBase; // Nested User object
  final String? description;
  final String? schedule;
  final String? room;
  final int maxStudents;
  final bool active;
  final String? fecha; // Assuming it comes as a string, might need DateTime.parse
  final GradeLevel? gradeLevel; // Nested GradeLevel object
  final String? periodo;
  final DateTime createdAt;

  Clase({
    required this.id,
    required this.name,
    this.subject,
    required this.cicloLectivo,
    required this.paralelo,
    this.docenteBase,
    this.description,
    this.schedule,
    this.room,
    required this.maxStudents,
    required this.active,
    this.fecha,
    this.gradeLevel,
    this.periodo,
    required this.createdAt,
  });

  factory Clase.fromJson(Map<String, dynamic> json) {
    return Clase(
      id: json['id'],
      name: json['name'],
      subject: json['subject'] != null ? Subject.fromJson(json['subject']) : null,
      cicloLectivo: json['ciclo_lectivo'],
      paralelo: json['paralelo'],
      docenteBase: json['docente_base'] != null ? User.fromJson(json['docente_base']) : null,
      description: json['description'],
      schedule: json['schedule'],
      room: json['room'],
      maxStudents: json['max_students'],
      active: json['active'],
      fecha: json['fecha'],
      gradeLevel: json['grade_level'] != null ? GradeLevel.fromJson(json['grade_level']) : null,
      periodo: json['periodo'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'subject': subject?.toJson(),
      'ciclo_lectivo': cicloLectivo,
      'paralelo': paralelo,
      'docente_base': docenteBase?.toJson(),
      'description': description,
      'schedule': schedule,
      'room': room,
      'max_students': maxStudents,
      'active': active,
      'fecha': fecha,
      'grade_level': gradeLevel?.toJson(),
      'periodo': periodo,
      'created_at': createdAt.toIso8601String(),
    };
  }
}