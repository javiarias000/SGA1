import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../models/activity.dart';
import '../providers/auth_provider.dart';

class ActivityProvider extends ChangeNotifier {
  final ApiService _api;
  final AuthProvider _auth;

  List<Activity> activities = [];
  bool isLoading = false;
  String errorMessage = '';

  ActivityProvider(this._api, this._auth);

  Future<void> fetchActividades({int? studentId, int? claseId, int? subjectId}) async {
    isLoading = true;
    errorMessage = '';
    notifyListeners();
    try {
      final data = await _api.fetchActividades(
        studentId: studentId,
        claseId: claseId,
        subjectId: subjectId,
        authToken: _auth.token,
      );
      activities = (data as List).map((e) => Activity.fromJson(e)).toList();
    } catch (e) {
      errorMessage = e.toString();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createActividad(Map<String, dynamic> data) async {
    try {
      final result = await _api.createActividad(data, authToken: _auth.token);
      activities.insert(0, Activity.fromJson(result));
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateActividad(int id, Map<String, dynamic> data) async {
    try {
      final result = await _api.updateActividad(id, data, authToken: _auth.token);
      final idx = activities.indexWhere((a) => a.id == id);
      if (idx != -1) activities[idx] = Activity.fromJson(result);
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteActividad(int id) async {
    try {
      await _api.deleteActividad(id, authToken: _auth.token);
      activities.removeWhere((a) => a.id == id);
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }
}
