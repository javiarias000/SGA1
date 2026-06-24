import 'grade_level.dart';
import 'subject.dart';
import 'user.dart';

class Horario {
  final int? id; // Assuming an ID field from the Django model
  final String dia;
  final String hora;
  final String aula;
  final GradeLevel? curso; // Nested GradeLevel object
  final User? docente; // Nested User object
  final Subject? clase; // Nested Subject object

  Horario({
    this.id,
    required this.dia,
    required this.hora,
    required this.aula,
    this.curso,
    this.docente,
    this.clase,
  });

  factory Horario.fromJson(Map<String, dynamic> json) {
    return Horario(
      id: json['id'],
      dia: json['dia'],
      hora: json['hora'],
      aula: json['aula'],
      curso: json['curso'] != null ? GradeLevel.fromJson(json['curso']) : null,
      docente: json['docente'] != null ? User.fromJson(json['docente']) : null,
      clase: json['clase'] != null ? Subject.fromJson(json['clase']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'dia': dia,
      'hora': hora,
      'aula': aula,
      'curso': curso?.toJson(),
      'docente': docente?.toJson(),
      'clase': clase?.toJson(),
    };
  }
}