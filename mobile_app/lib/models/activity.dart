int _i(dynamic v, [int def = 0]) => v == null ? def : (v as num).toInt();
int? _iN(dynamic v) => v == null ? null : (v as num).toInt();

class Activity {
  final int id;
  final int studentId;
  final int claseId;
  final int? subjectId;
  final String subjectNombre;
  final int classNumber;
  final DateTime date;
  final String topicsWorked;
  final String techniques;
  final String pieces;
  final String performance;
  final String strengths;
  final String areasToImprove;
  final String homework;
  final int practiceTime;
  final String observations;

  const Activity({
    required this.id,
    required this.studentId,
    required this.claseId,
    this.subjectId,
    required this.subjectNombre,
    required this.classNumber,
    required this.date,
    required this.topicsWorked,
    required this.techniques,
    required this.pieces,
    required this.performance,
    required this.strengths,
    required this.areasToImprove,
    required this.homework,
    required this.practiceTime,
    required this.observations,
  });

  factory Activity.fromJson(Map<String, dynamic> j) => Activity(
        id: _i(j['id']),
        studentId: _i(j['student']),
        claseId: _i(j['clase']),
        subjectId: _iN(j['subject']),
        subjectNombre: j['subject_nombre']?.toString() ?? '',
        classNumber: _i(j['class_number']),
        date: DateTime.tryParse(j['date']?.toString() ?? '') ?? DateTime.now(),
        topicsWorked: j['topics_worked']?.toString() ?? '',
        techniques: j['techniques']?.toString() ?? '',
        pieces: j['pieces']?.toString() ?? '',
        performance: j['performance']?.toString() ?? 'Bueno',
        strengths: j['strengths']?.toString() ?? '',
        areasToImprove: j['areas_to_improve']?.toString() ?? '',
        homework: j['homework']?.toString() ?? '',
        practiceTime: _i(j['practice_time'], 30),
        observations: j['observations']?.toString() ?? '',
      );

  Map<String, dynamic> toJson() => {
        'student': studentId,
        'clase': claseId,
        if (subjectId != null) 'subject': subjectId,
        'date': date.toIso8601String().split('T').first,
        'topics_worked': topicsWorked,
        'techniques': techniques,
        'pieces': pieces,
        'performance': performance,
        'strengths': strengths,
        'areas_to_improve': areasToImprove,
        'homework': homework,
        'practice_time': practiceTime,
        'observations': observations,
      };
}
