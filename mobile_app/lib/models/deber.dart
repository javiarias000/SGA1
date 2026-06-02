class Deber {
  final int id;
  final String titulo;
  final String descripcion;
  final DateTime fechaAsignacion;
  final DateTime fechaEntrega;
  final int? teacherId;
  final int? claseId;
  final double puntosTotales;
  final String estado;
  final int entregasCompletadas;
  final double porcentajeEntrega;

  const Deber({
    required this.id,
    required this.titulo,
    required this.descripcion,
    required this.fechaAsignacion,
    required this.fechaEntrega,
    this.teacherId,
    this.claseId,
    required this.puntosTotales,
    required this.estado,
    required this.entregasCompletadas,
    required this.porcentajeEntrega,
  });

  bool get estaVencido => DateTime.now().isAfter(fechaEntrega);

  factory Deber.fromJson(Map<String, dynamic> j) => Deber(
        id: j['id'] as int,
        titulo: j['titulo']?.toString() ?? '',
        descripcion: j['descripcion']?.toString() ?? '',
        fechaAsignacion: DateTime.tryParse(j['fecha_asignacion']?.toString() ?? '') ?? DateTime.now(),
        fechaEntrega: DateTime.tryParse(j['fecha_entrega']?.toString() ?? '') ?? DateTime.now(),
        teacherId: j['teacher'] as int?,
        claseId: j['clase'] as int?,
        puntosTotales: (j['puntos_totales'] as num?)?.toDouble() ?? 10.0,
        estado: j['estado']?.toString() ?? 'activo',
        entregasCompletadas: (j['entregas_completadas'] as int?) ?? 0,
        porcentajeEntrega: (j['porcentaje_entrega'] as num?)?.toDouble() ?? 0.0,
      );
}

class DeberEntrega {
  final int id;
  final int deberId;
  final String deberTitulo;
  final int estudianteId;
  final String estudianteNombre;
  final DateTime fechaEntrega;
  final String comentario;
  final double? calificacion;
  final String retroalimentacion;
  final String estado;

  const DeberEntrega({
    required this.id,
    required this.deberId,
    required this.deberTitulo,
    required this.estudianteId,
    required this.estudianteNombre,
    required this.fechaEntrega,
    required this.comentario,
    this.calificacion,
    required this.retroalimentacion,
    required this.estado,
  });

  factory DeberEntrega.fromJson(Map<String, dynamic> j) => DeberEntrega(
        id: j['id'] as int,
        deberId: j['deber'] as int? ?? 0,
        deberTitulo: j['deber_titulo']?.toString() ?? '',
        estudianteId: j['estudiante'] as int? ?? 0,
        estudianteNombre: j['estudiante_nombre']?.toString() ?? '',
        fechaEntrega: DateTime.tryParse(j['fecha_entrega']?.toString() ?? '') ?? DateTime.now(),
        comentario: j['comentario']?.toString() ?? '',
        calificacion: (j['calificacion'] as num?)?.toDouble(),
        retroalimentacion: j['retroalimentacion']?.toString() ?? '',
        estado: j['estado']?.toString() ?? 'pendiente',
      );
}
