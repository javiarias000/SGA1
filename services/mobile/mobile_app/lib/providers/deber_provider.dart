import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../models/deber.dart';
import '../providers/auth_provider.dart';

class DeberProvider extends ChangeNotifier {
  final ApiService _api;
  final AuthProvider _auth;

  List<Deber> deberes = [];
  List<DeberEntrega> entregas = [];
  List<DeberEntrega> misEntregas = [];
  bool isLoading = false;
  String errorMessage = '';

  DeberProvider(this._api, this._auth);

  Future<void> fetchDeberes({int? claseId, String? estado}) async {
    isLoading = true;
    errorMessage = '';
    notifyListeners();
    try {
      final data = await _api.fetchDeberes(
        claseId: claseId,
        estado: estado,
        authToken: _auth.token,
      );
      deberes = (data as List).map((e) => Deber.fromJson(e)).toList();
    } catch (e) {
      errorMessage = e.toString();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchMisEntregas(int estudianteId) async {
    isLoading = true;
    errorMessage = '';
    notifyListeners();
    try {
      final data = await _api.fetchMisEntregas(
        estudianteId: estudianteId,
        authToken: _auth.token,
      );
      misEntregas = (data as List).map((e) => DeberEntrega.fromJson(e)).toList();
    } catch (e) {
      errorMessage = e.toString();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchEntregas(int deberId) async {
    isLoading = true;
    errorMessage = '';
    notifyListeners();
    try {
      final data = await _api.fetchEntregasDeber(deberId, authToken: _auth.token);
      entregas = (data as List).map((e) => DeberEntrega.fromJson(e)).toList();
    } catch (e) {
      errorMessage = e.toString();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createDeber(Map<String, dynamic> data) async {
    try {
      final result = await _api.createDeber(data, authToken: _auth.token);
      deberes.insert(0, Deber.fromJson(result));
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteDeber(int id) async {
    try {
      await _api.deleteDeber(id, authToken: _auth.token);
      deberes.removeWhere((d) => d.id == id);
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> crearEntrega(Map<String, dynamic> data) async {
    try {
      final result = await _api.crearEntrega(data, authToken: _auth.token);
      misEntregas.insert(0, DeberEntrega.fromJson(result));
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> calificarEntrega(int id, double calificacion, String retroalimentacion) async {
    try {
      await _api.calificarEntrega(id, {
        'calificacion': calificacion,
        'retroalimentacion': retroalimentacion,
        'estado': 'revisado',
      }, authToken: _auth.token);
      final idx = entregas.indexWhere((e) => e.id == id);
      if (idx != -1) {
        entregas[idx] = DeberEntrega.fromJson({
          ...entregas[idx].toJson(),
          'calificacion': calificacion,
          'retroalimentacion': retroalimentacion,
          'estado': 'revisado',
        });
      }
      notifyListeners();
      return true;
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }
}

extension DeberEntregaJson on DeberEntrega {
  Map<String, dynamic> toJson() => {
        'id': id,
        'deber': deberId,
        'deber_titulo': deberTitulo,
        'estudiante': estudianteId,
        'estudiante_nombre': estudianteNombre,
        'fecha_entrega': fechaEntrega.toIso8601String(),
        'comentario': comentario,
        'calificacion': calificacion,
        'retroalimentacion': retroalimentacion,
        'estado': estado,
      };
}
