import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart'; // Import Provider
import 'package:mobile_app/api/api_service.dart';
import 'package:mobile_app/models/horario.dart';
import 'package:mobile_app/services/auth_service.dart';
import 'package:mobile_app/router/app_router.dart';
import 'package:mobile_app/providers/auth_provider.dart'; // Import AuthProvider
import 'package:mobile_app/providers/horario_provider.dart'; // Import HorarioProvider
import 'package:mobile_app/providers/student_provider.dart';
import 'package:mobile_app/providers/teacher_provider.dart';
import 'package:mobile_app/providers/clase_provider.dart';
import 'package:mobile_app/providers/subject_provider.dart';

void main() {
  final ApiService apiService = ApiService();
  final AuthService authService = AuthService(apiService);

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => apiService),
        Provider<AuthService>(create: (_) => authService),
        ChangeNotifierProvider<AuthProvider>(
          create: (context) => AuthProvider(authService),
        ),
        ChangeNotifierProxyProvider<AuthProvider, HorarioProvider>(
          create: (context) => HorarioProvider(
            context.read<ApiService>(),
            context.read<AuthProvider>(),
          ),
          update: (context, auth, previous) => HorarioProvider(
            context.read<ApiService>(),
            auth,
          ),
        ),
        ChangeNotifierProxyProvider<AuthProvider, StudentProvider>(
          create: (context) => StudentProvider(
            context.read<ApiService>(),
            context.read<AuthProvider>(),
          ),
          update: (context, auth, previous) => StudentProvider(
            context.read<ApiService>(),
            auth,
          ),
        ),
        ChangeNotifierProxyProvider<AuthProvider, TeacherProvider>(
          create: (context) => TeacherProvider(
            context.read<ApiService>(),
            context.read<AuthProvider>(),
          ),
          update: (context, auth, previous) => TeacherProvider(
            context.read<ApiService>(),
            auth,
          ),
        ),
        ChangeNotifierProxyProvider<AuthProvider, ClaseProvider>(
          create: (context) => ClaseProvider(
            context.read<ApiService>(),
            context.read<AuthProvider>(),
          ),
          update: (context, auth, previous) => ClaseProvider(
            context.read<ApiService>(),
            auth,
          ),
        ),
        ChangeNotifierProvider<SubjectProvider>(
          create: (context) => SubjectProvider(Provider.of<ClaseProvider>(context, listen: false)),
        ),
      ],
      child: MyApp(authService: authService), // Pass authService for GoRouter
    ),
  );
}

class MyApp extends StatelessWidget {
  final AuthService authService; // Required for AppRouter initialization
  const MyApp({super.key, required this.authService});

  @override
  Widget build(BuildContext context) {
    // AppRouter needs to be created after AuthProvider is available in the context
    final AppRouter appRouter = AppRouter(authService: authService, apiService: Provider.of<ApiService>(context));

    return MaterialApp.router(
      title: 'Flutter Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      routerConfig: appRouter.router,
    );
  }
}

// LoginScreen and MyHomePage classes remain here for now.

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  String _errorMessage = '';
  bool _isLoading = false;

  Future<void> _login() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final success = await authProvider.login(
        _usernameController.text,
        _passwordController.text,
      );

      if (!mounted) return; // Check if the widget is still in the tree

      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Login successful!')),
        );
        GoRouter.of(context).go('/');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Login failed. Please check your credentials.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('An error occurred: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Login'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextField(
                controller: _usernameController,
                decoration: const InputDecoration(
                  labelText: 'Username',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Password',
                ),
                onSubmitted: (_) => _login(),
              ),
              const SizedBox(height: 16),
              if (_isLoading)
                const CircularProgressIndicator()
              else
                ElevatedButton(
                  onPressed: _login,
                  child: const Text('Login'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({
    super.key,
    required this.title,
  }); // Removed authService, apiService, onLogout

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  @override
  void initState() {
    super.initState();
    // Fetch horarios when the page initializes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<HorarioProvider>(context, listen: false).fetchHorarios();
    });
  }

  @override
  Widget build(BuildContext context) {
    // Watch the HorarioProvider for changes
    final horarioProvider = Provider.of<HorarioProvider>(context);
    final authProvider = Provider.of<AuthProvider>(context, listen: false); // For logout

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await authProvider.logout();
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Logged out successfully.')),
                );
                GoRouter.of(context).go('/login'); // Redirect to login after logout
              }
            },
            tooltip: 'Logout',
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView( // Added SingleChildScrollView
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              horarioProvider.isLoading
                  ? const CircularProgressIndicator()
                  : horarioProvider.errorMessage.isNotEmpty
                      ? Text(
                          horarioProvider.errorMessage,
                          style: const TextStyle(color: Colors.red),
                          textAlign: TextAlign.center,
                        )
                      : horarioProvider.horarios.isEmpty
                          ? const Text('No horarios available.')
                          : ListView.builder(
                              shrinkWrap: true, // Use shrinkWrap here
                              physics: const NeverScrollableScrollPhysics(), // Disable scrolling here
                              itemCount: horarioProvider.horarios.length,
                              itemBuilder: (context, index) {
                                final horario = horarioProvider.horarios[index];
                                return Card(
                                  margin: const EdgeInsets.all(8.0),
                                  child: ListTile(
                                    title: Text(
                                      'Día: ${horario.dia}',
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    subtitle: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Hora: ${horario.hora}'),
                                        Text('Aula: ${horario.aula}'),
                                        Text('Curso: ${horario.curso?.level} ${horario.curso?.section ?? "N/A"}'),
                                        Text('Docente: ${horario.docente?.nombre ?? "N/A"}'),
                                        Text('Clase: ${horario.clase?.name ?? "N/A"}'),
                                      ],
                                    ),
                                    onTap: () {
                                      if (horario.id != null) {
                                        GoRouter.of(context).go('/horarios/${horario.id}');
                                      } else {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          const SnackBar(content: Text('Horario ID is missing!')),
                                        );
                                      }
                                    },
                                  ),
                                );
                              },
                            ),
              const SizedBox(height: 20), // Add some spacing
              ElevatedButton(
                onPressed: () {
                  GoRouter.of(context).go('/students');
                },
                child: const Text('View Students'),
              ),
              const SizedBox(height: 10), // Add some spacing between buttons
              ElevatedButton(
                onPressed: () {
                  GoRouter.of(context).go('/teachers');
                },
                child: const Text('View Teachers'),
              ),
              const SizedBox(height: 10), // Add some spacing between buttons
              ElevatedButton(
                onPressed: () {
                  GoRouter.of(context).go('/subjects');
                },
                child: const Text('View Subjects'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

