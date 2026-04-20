import 'user.dart';

class Teacher {
  final int id;
  final User usuario; // Nested User object
  final String? specialization;
  final String? photo;
  final String? fullName; // Derived field

  Teacher({
    required this.id,
    required this.usuario,
    this.specialization,
    this.photo,
    this.fullName,
  });

  factory Teacher.fromJson(Map<String, dynamic> json) {
    return Teacher(
      id: json['id'],
      usuario: User.fromJson(json['usuario']),
      specialization: json['specialization'],
      photo: json['photo'],
      fullName: json['full_name'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'usuario': usuario.toJson(),
      'specialization': specialization,
      'photo': photo,
      'full_name': fullName,
    };
  }
}