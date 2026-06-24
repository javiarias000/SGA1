import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../api/api_service.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common_widgets.dart';

const _instrumentos = [
  'Piano', 'Guitarra', 'Violín', 'Viola', 'Violonchelo', 'Contrabajo',
  'Flauta Traversa', 'Oboe', 'Clarinete', 'Fagot', 'Trompeta', 'Trombón',
  'Corno Francés', 'Tuba', 'Saxofón', 'Percusión', 'Arpa', 'Canto', 'Acordeón',
];

class NuevaMatriculaScreen extends StatefulWidget {
  const NuevaMatriculaScreen({super.key});

  @override
  State<NuevaMatriculaScreen> createState() => _NuevaMatriculaScreenState();
}

class _NuevaMatriculaScreenState extends State<NuevaMatriculaScreen> {
  final _formKey = GlobalKey<FormState>();
  int _paso = 1;
  bool _saving = false;

  // Paso 1 — datos personales
  final _nombreCtrl = TextEditingController();
  final _cedulaCtrl = TextEditingController();
  final _fechaNacCtrl = TextEditingController();
  final _reprNombreCtrl = TextEditingController();
  final _reprEmailCtrl = TextEditingController();
  final _reprPhoneCtrl = TextEditingController();
  final _direccionCtrl = TextEditingController();
  final _ciudadCtrl = TextEditingController();
  String _instrumento = _instrumentos.first;
  int _anio = 1;

  // Paso 2 — archivos
  File? _cedulaDoc;
  File? _certEdDoc;
  File? _certConsDoc;
  File? _fotoDoc;

  @override
  void dispose() {
    for (final c in [_nombreCtrl, _cedulaCtrl, _fechaNacCtrl, _reprNombreCtrl,
                     _reprEmailCtrl, _reprPhoneCtrl, _direccionCtrl, _ciudadCtrl]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickFile(Function(File) onPicked) async {
    final result = await FilePicker.platform.pickFiles(type: FileType.any);
    if (result != null && result.files.single.path != null) {
      onPicked(File(result.files.single.path!));
    }
  }

  Future<void> _submit() async {
    if (_cedulaDoc == null || _certEdDoc == null || _fotoDoc == null) {
      _snack('Adjunta los documentos requeridos (cédula, certificado y foto).');
      return;
    }
    setState(() => _saving = true);
    try {
      final api = context.read<ApiService>();
      final auth = context.read<AuthProvider>();
      final datos = {
        'nombre_completo': _nombreCtrl.text,
        'cedula': _cedulaCtrl.text,
        'fecha_nacimiento': _fechaNacCtrl.text,
        'nombre_representante': _reprNombreCtrl.text,
        'email_representante': _reprEmailCtrl.text,
        'phone_representante': _reprPhoneCtrl.text,
        'direccion': _direccionCtrl.text,
        'ciudad': _ciudadCtrl.text,
        'anio_solicitado': _anio,
        'instrumento_elegido': _instrumento,
      };
      final archivos = <String, File>{
        'cedula_doc': _cedulaDoc!,
        'cert_educacion_doc': _certEdDoc!,
        'foto_carnet_doc': _fotoDoc!,
        if (_certConsDoc != null) 'cert_conservatorio_doc': _certConsDoc!,
      };
      final result = await api.crearMatricula(datos, archivos, authToken: auth.authToken);
      if (!mounted) return;
      final codigo = result['codigo']?.toString() ?? '';
      context.pushReplacement('/matriculas/confirmacion?codigo=$codigo&nombre=${_nombreCtrl.text}');
    } catch (e) {
      if (mounted) _snack('Error al enviar: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Matriculación — Paso $_paso de 2'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(
            value: _paso / 2,
            backgroundColor: Colors.white24,
            valueColor: const AlwaysStoppedAnimation<Color>(AppColors.gold),
          ),
        ),
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: _paso == 1 ? _buildPaso1() : _buildPaso2(),
        ),
      ),
    );
  }

  Widget _buildPaso1() {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const Text('Datos del estudiante', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      const SizedBox(height: 16),
      _field(_nombreCtrl, 'Nombre completo', required: true),
      const SizedBox(height: 12),
      _field(_cedulaCtrl, 'Cédula de identidad', required: true),
      const SizedBox(height: 12),
      _field(_fechaNacCtrl, 'Fecha de nacimiento (YYYY-MM-DD)', required: true, hint: '2010-06-15'),
      const SizedBox(height: 20),
      const Text('Datos del representante', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      const SizedBox(height: 16),
      _field(_reprNombreCtrl, 'Nombre del representante'),
      const SizedBox(height: 12),
      _field(_reprEmailCtrl, 'Email del representante', required: true, keyboardType: TextInputType.emailAddress),
      const SizedBox(height: 12),
      _field(_reprPhoneCtrl, 'Teléfono', required: true, keyboardType: TextInputType.phone),
      const SizedBox(height: 12),
      _field(_direccionCtrl, 'Dirección'),
      const SizedBox(height: 12),
      _field(_ciudadCtrl, 'Ciudad'),
      const SizedBox(height: 20),
      const Text('Información académica', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      const SizedBox(height: 16),
      DropdownButtonFormField<int>(
        value: _anio,
        decoration: const InputDecoration(labelText: 'Año de estudio'),
        items: List.generate(11, (i) => DropdownMenuItem(value: i + 1, child: Text('${i + 1}° año'))),
        onChanged: (v) => setState(() => _anio = v ?? 1),
      ),
      const SizedBox(height: 12),
      DropdownButtonFormField<String>(
        value: _instrumento,
        decoration: const InputDecoration(labelText: 'Instrumento'),
        items: _instrumentos.map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
        onChanged: (v) => setState(() => _instrumento = v ?? _instrumentos.first),
      ),
      const SizedBox(height: 28),
      ElevatedButton(
        onPressed: () {
          if (_formKey.currentState!.validate()) setState(() => _paso = 2);
        },
        child: const Text('Siguiente → Documentos'),
      ),
    ]);
  }

  Widget _buildPaso2() {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const Text('Adjunta los documentos requeridos', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      const SizedBox(height: 6),
      const Text('Formatos aceptados: PDF, JPG, PNG (máx. 5MB)',
          style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
      const SizedBox(height: 20),
      _filePicker('Cédula de identidad *', _cedulaDoc, (f) => setState(() => _cedulaDoc = f)),
      const SizedBox(height: 12),
      _filePicker('Certificado de educación regular *', _certEdDoc, (f) => setState(() => _certEdDoc = f)),
      const SizedBox(height: 12),
      _filePicker('Certificado del conservatorio (2°+ año)', _certConsDoc, (f) => setState(() => _certConsDoc = f)),
      const SizedBox(height: 12),
      _filePicker('Foto carnet *', _fotoDoc, (f) => setState(() => _fotoDoc = f)),
      const SizedBox(height: 28),
      Row(children: [
        Expanded(
          child: OutlinedButton(
            onPressed: () => setState(() => _paso = 1),
            child: const Text('← Volver'),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          flex: 2,
          child: _saving
              ? const Center(child: CircularProgressIndicator())
              : ElevatedButton.icon(
                  onPressed: _submit,
                  icon: const Icon(Icons.send),
                  label: const Text('Enviar solicitud'),
                ),
        ),
      ]),
    ]);
  }

  Widget _field(TextEditingController ctrl, String label, {
    bool required = false,
    TextInputType keyboardType = TextInputType.text,
    String? hint,
  }) {
    return TextFormField(
      controller: ctrl,
      keyboardType: keyboardType,
      decoration: InputDecoration(labelText: label, hintText: hint),
      validator: required ? (v) => (v == null || v.trim().isEmpty) ? 'Requerido' : null : null,
    );
  }

  Widget _filePicker(String label, File? file, Function(File) onPicked) {
    return InkWell(
      onTap: () => _pickFile(onPicked),
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: file != null ? AppColors.success.withOpacity(0.05) : Colors.white,
          border: Border.all(
            color: file != null ? AppColors.success : AppColors.divider,
            width: file != null ? 1.5 : 1,
          ),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(children: [
          Icon(
            file != null ? Icons.check_circle : Icons.upload_file,
            color: file != null ? AppColors.success : AppColors.textMuted,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
              Text(
                file != null ? file.path.split('/').last : 'Toca para seleccionar archivo',
                style: TextStyle(
                  fontSize: 11,
                  color: file != null ? AppColors.success : AppColors.textMuted,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ]),
          ),
          Icon(Icons.chevron_right, color: AppColors.textMuted, size: 18),
        ]),
      ),
    );
  }
}
