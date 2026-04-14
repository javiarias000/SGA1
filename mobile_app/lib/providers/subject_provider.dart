import 'package:flutter/material.dart';
import 'package:mobile_app/models/subject.dart';
import 'package:mobile_app/providers/clase_provider.dart';
import 'package:mobile_app/models/clase.dart';
import 'package:mobile_app/models/teacher.dart';

class SubjectProvider extends ChangeNotifier {
  final ClaseProvider _claseProvider;
  List<Subject> _subjects = [];
  bool _isLoading = false;
  String _errorMessage = '';

  Subject? _selectedSubject;
  List<Teacher> _associatedTeachers = [];

  SubjectProvider(this._claseProvider) {
    _claseProvider.addListener(_onClasesUpdated);
    _onClasesUpdated();
  }

  List<Subject> get subjects => _subjects;
  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;
  Subject? get selectedSubject => _selectedSubject;
  List<Teacher> get associatedTeachers => _associatedTeachers;

  void _onClasesUpdated() {
    _isLoading = _claseProvider.isLoading;
    _errorMessage = _claseProvider.errorMessage;
    if (_errorMessage.isEmpty) {
      _extractUniqueSubjects(_claseProvider.clases);
    }
    notifyListeners();
  }

  void _extractUniqueSubjects(List<Clase> clases) {
    final Set<int> seenSubjectIds = {};
    final List<Subject> uniqueSubjects = [];

    for (var clase in clases) {
      if (clase.subject != null && !seenSubjectIds.contains(clase.subject!.id)) {
        uniqueSubjects.add(clase.subject!);
        seenSubjectIds.add(clase.subject!.id);
      }
    }
    _subjects = uniqueSubjects;
  }

  void selectSubject(int subjectId) {
    clearSelection();
    try {
      _selectedSubject = _subjects.firstWhere((s) => s.id == subjectId);

      final Set<int> seenTeacherIds = {};
      final List<Teacher> teachers = [];
      
      final relevantClases = _claseProvider.clases.where((c) => c.subject?.id == subjectId);

      for (var clase in relevantClases) {
        if (clase.teacher != null && !seenTeacherIds.contains(clase.teacher!.id)) {
          teachers.add(clase.teacher!);
          seenTeacherIds.add(clase.teacher!.id);
        }
      }
      _associatedTeachers = teachers;

    } catch (e) {
      _errorMessage = "Subject with ID $subjectId not found.";
    }
    notifyListeners();
  }

  void clearSelection() {
    _selectedSubject = null;
    _associatedTeachers = [];
    _errorMessage = '';
    notifyListeners();
  }

  @override
  void dispose() {
    _claseProvider.removeListener(_onClasesUpdated);
    super.dispose();
  }
}