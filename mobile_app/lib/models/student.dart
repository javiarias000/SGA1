import 'user.dart';

class Student {
  final int id;
  final User? usuario; // Nested User object
  final int? teacherId; // Foreign Key to Teacher
  final int? gradeLevelId; // Foreign Key to GradeLevel
  final String? parentName;
  final String? parentEmail;
  final String? parentPhone;
  final String? notes;
  final String? photo;
  final bool active;
  final String? registrationCode;
  final DateTime createdAt;
  final String? name; // Derived field
  final String? gradeLevelName; // Derived field
  final String? teacherFullName; // Derived field

  Student({
    required this.id,
    this.usuario,
    this.teacherId,
    this.gradeLevelId,
    this.parentName,
    this.parentEmail,
    this.parentPhone,
    this.notes,
    this.photo,
    required this.active,
    this.registrationCode,
    required this.createdAt,
    this.name,
    this.gradeLevelName,
    this.teacherFullName,
  });

  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      id: json['id'],
      usuario: json['usuario'] != null ? User.fromJson(json['usuario']) : null,
      teacherId: json['teacher'], // Assuming this returns the FK ID
      gradeLevelId: json['grade_level'], // Assuming this returns the FK ID
      parentName: json['parent_name'],
      parentEmail: json['parent_email'],
      parentPhone: json['parent_phone'],
      notes: json['notes'],
      photo: json['photo'],
      active: json['active'],
      registrationCode: json['registration_code'],
      createdAt: DateTime.parse(json['created_at']),
      name: json['name'],
      gradeLevelName: json['grade_level_name'],
      teacherFullName: json['teacher_full_name'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'usuario': usuario?.toJson(),
      'teacher': teacherId,
      'grade_level': gradeLevelId,
      'parent_name': parentName,
      'parent_email': parentEmail,
      'parent_phone': parentPhone,
      'notes': notes,
      'photo': photo,
      'active': active,
      'registration_code': registrationCode,
      'created_at': createdAt.toIso8601String(),
      'name': name,
      'grade_level_name': gradeLevelName,
      'teacher_full_name': teacherFullName,
    };
  }
}