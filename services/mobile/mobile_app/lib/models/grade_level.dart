import 'user.dart';

class GradeLevel {
  final int id;
  final String level;
  final String section;
  final User? docenteTutor; // Nested User object, can be null

  GradeLevel({
    required this.id,
    required this.level,
    required this.section,
    this.docenteTutor,
  });

  factory GradeLevel.fromJson(Map<String, dynamic> json) {
    return GradeLevel(
      id: json['id'],
      level: json['level'],
      section: json['section'],
      docenteTutor: json['docente_tutor'] != null
          ? User.fromJson(json['docente_tutor'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'level': level,
      'section': section,
      'docente_tutor': docenteTutor?.toJson(),
    };
  }
}