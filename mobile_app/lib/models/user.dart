class User {
  final int id;
  final String nombre;
  final String email;
  final String? phone;
  final String? cedula;
  final String rol;

  User({
    required this.id,
    required this.nombre,
    required this.email,
    this.phone,
    this.cedula,
    required this.rol,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      nombre: json['nombre'] ?? '',
      email: json['email'] ?? '',
      phone: json['phone'],
      cedula: json['cedula'],
      rol: json['rol'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'nombre': nombre,
      'email': email,
      'phone': phone,
      'cedula': cedula,
      'rol': rol,
    };
  }
}