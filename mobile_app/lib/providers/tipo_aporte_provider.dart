import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../models/tipo_aporte.dart';
import '../providers/auth_provider.dart';

class TipoAporteProvider extends ChangeNotifier {
  final ApiService _api;
  final AuthProvider _auth;

  List<TipoAporte> tiposAporte = [];
  bool isLoading = false;
  String errorMessage = '';

  TipoAporteProvider(this._api, this._auth);

  Future<void> fetchTiposAporte() async {
    isLoading = true;
    errorMessage = '';
    notifyListeners();
    try {
      final data = await _api.fetchTiposAporte(authToken: _auth.token);
      tiposAporte = (data as List).map((e) => TipoAporte.fromJson(e)).toList();
    } catch (e) {
      errorMessage = e.toString();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}
