class Subject {
  final int id;
  final String name;
  final String description;
  final String tipoMateria;

  Subject({
    required this.id,
    required this.name,
    required this.description,
    required this.tipoMateria,
  });

  factory Subject.fromJson(Map<String, dynamic> json) {
    return Subject(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      tipoMateria: json['tipo_materia'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'tipo_materia': tipoMateria,
    };
  }
}