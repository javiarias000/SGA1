class ApiConfig {
  // Configurable via --dart-define=API_URL=http://...
  // Android emulator default: 10.0.2.2:8000
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}

class GradeLabels {
  static String nivel(double? nota) {
    if (nota == null) return '—';
    if (nota >= 9) return 'DAR';
    if (nota >= 7) return 'AAR';
    if (nota > 4) return 'PAAR';
    return 'NAAR';
  }

  static String nivelLabel(double? nota) {
    if (nota == null) return 'Sin datos';
    if (nota >= 9) return 'Domina los Aprendizajes';
    if (nota >= 7) return 'Alcanza los Aprendizajes';
    if (nota > 4) return 'Próximo a Alcanzar';
    return 'No Alcanza';
  }
}
