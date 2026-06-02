class TipoAporte {
  final int id;
  final String nombre;
  final String codigo;
  final String descripcion;
  final double peso;
  final int orden;
  final bool activo;

  const TipoAporte({
    required this.id,
    required this.nombre,
    required this.codigo,
    required this.descripcion,
    required this.peso,
    required this.orden,
    required this.activo,
  });

  factory TipoAporte.fromJson(Map<String, dynamic> j) => TipoAporte(
        id: j['id'] as int,
        nombre: j['nombre']?.toString() ?? '',
        codigo: j['codigo']?.toString() ?? '',
        descripcion: j['descripcion']?.toString() ?? '',
        peso: (j['peso'] as num?)?.toDouble() ?? 1.0,
        orden: (j['orden'] as int?) ?? 0,
        activo: j['activo'] as bool? ?? true,
      );
}
