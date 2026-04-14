import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mobile_app/providers/auth_provider.dart';
import 'package:mobile_app/services/auth_service.dart';

// Manual mock of AuthService
class MockAuthService extends Mock implements AuthService {}

void main() {
  late MockAuthService mockAuthService;
  late AuthProvider authProvider;

  // Set up the mocks before each test
      setUp(() {
        mockAuthService = MockAuthService();
        authProvider = AuthProvider(mockAuthService);
        // Default mock for getAuthToken as AuthProvider calls it during initialization
        when(mockAuthService.getAuthToken()).thenAnswer((_) async => null);
      });
  group('AuthProvider', () {
    test('initial state is logged out', () {
      // Assert
      expect(authProvider.isLoggedIn, false);
    });

    test('login success updates isLoggedIn to true', () async {
      // Arrange: When login is called on the mock service, return true
      when(mockAuthService.login(any<String>(), any<String>())).thenAnswer((_) async => true);
      
      // Act: Call the login method on the provider
      final result = await authProvider.login('testuser', 'password');
      
      // Assert: Verify that the login was successful and the state updated
      expect(result, true);
      expect(authProvider.isLoggedIn, true);
    });

    test('login failure keeps isLoggedIn as false', () async {
      // Arrange: When login is called, return false
      when(mockAuthService.login(any<String>(), any<String>())).thenAnswer((_) async => false);

      // Act
      final result = await authProvider.login('testuser', 'wrongpassword');

      // Assert
      expect(result, false);
      expect(authProvider.isLoggedIn, false);
    });

    test('logout updates isLoggedIn to false', () async {
      // Arrange: First, simulate a successful login
      when(mockAuthService.login(any<String>(), any<String>())).thenAnswer((_) async => true);
      await authProvider.login('testuser', 'password');
      expect(authProvider.isLoggedIn, true); // Pre-condition check

      // Arrange for logout: when logout is called, complete successfully
      when(mockAuthService.logout()).thenAnswer((_) async => {});

      // Act: Call logout
      await authProvider.logout();

      // Assert: Verify isLoggedIn is now false
      expect(authProvider.isLoggedIn, false);
    });

    test('getAuthToken calls the underlying service', () async {
      // Arrange
      const token = 'test_token';
      when(mockAuthService.getAuthToken()).thenAnswer((_) async => token);

      // Act
      final result = await authProvider.authToken;

      // Assert
      expect(result, token);
      verify(mockAuthService.getAuthToken()).called(1); // Verify the service method was called
    });
  });
}
