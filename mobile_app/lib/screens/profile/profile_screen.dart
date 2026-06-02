import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common_widgets.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final nombre = auth.userName ?? 'Usuario';
    final rol = auth.userRole ?? '';
    final email = auth.userEmail ?? '';

    return Scaffold(
      appBar: AppBar(title: const Text('Mi Perfil')),
      body: SingleChildScrollView(
        child: Column(children: [
          // Avatar header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(32),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [AppColors.primary, AppColors.primary700],
                begin: Alignment.topLeft, end: Alignment.bottomRight,
              ),
            ),
            child: Column(children: [
              CircleAvatar(
                radius: 40,
                backgroundColor: AppColors.gold,
                child: Text(
                  nombre.isNotEmpty ? nombre[0].toUpperCase() : '?',
                  style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: AppColors.primary),
                ),
              ),
              const SizedBox(height: 12),
              Text(nombre, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.gold.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(rol, style: const TextStyle(color: AppColors.gold, fontSize: 12)),
              ),
              if (email.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(email, style: const TextStyle(color: Colors.white60, fontSize: 12)),
              ],
            ]),
          ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              const SectionHeader(title: 'Mi cuenta'),
              Card(
                child: Column(children: [
                  ListTile(
                    leading: const Icon(Icons.person_outline, color: AppColors.primary),
                    title: const Text('Nombre completo'),
                    subtitle: Text(nombre),
                  ),
                  if (email.isNotEmpty) ...[
                    const Divider(height: 1, indent: 56),
                    ListTile(
                      leading: const Icon(Icons.email_outlined, color: AppColors.primary),
                      title: const Text('Email'),
                      subtitle: Text(email),
                    ),
                  ],
                  const Divider(height: 1, indent: 56),
                  ListTile(
                    leading: const Icon(Icons.badge_outlined, color: AppColors.primary),
                    title: const Text('Rol'),
                    subtitle: Text(rol),
                  ),
                ]),
              ),

              const SizedBox(height: 16),
              const SectionHeader(title: 'Acciones'),
              Card(
                child: Column(children: [
                  if (auth.userRole != 'ESTUDIANTE') ...[
                    ListTile(
                      leading: const Icon(Icons.school_outlined, color: AppColors.primary),
                      title: const Text('Estudiantes'),
                      trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
                      onTap: () => context.push('/students'),
                    ),
                    const Divider(height: 1, indent: 56),
                  ],
                  ListTile(
                    leading: const Icon(Icons.assignment_outlined, color: AppColors.primary),
                    title: const Text('Mis matrículas'),
                    trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
                    onTap: () => context.push('/matriculas/seguimiento'),
                  ),
                ]),
              ),

              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () async {
                    await context.read<AuthProvider>().logout();
                    if (context.mounted) context.go('/login');
                  },
                  icon: const Icon(Icons.logout, color: AppColors.error),
                  label: const Text('Cerrar sesión', style: TextStyle(color: AppColors.error)),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.error),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ]),
          ),
        ]),
      ),
    );
  }
}
