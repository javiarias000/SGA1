import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  static const Color primary    = Color(0xFF00204A); // cb-blue-900
  static const Color primary700 = Color(0xFF004299); // cb-blue-700
  static const Color primary600 = Color(0xFF0056CC);
  static const Color gold       = Color(0xFFFCCB00);
  static const Color goldDark   = Color(0xFFB38600);
  static const Color surface    = Color(0xFFF8FAFF);
  static const Color error      = Color(0xFFDC2626);
  static const Color success    = Color(0xFF16A34A);
  static const Color warning    = Color(0xFFD97706);
  static const Color textDark   = Color(0xFF0F172A);
  static const Color textMuted  = Color(0xFF64748B);
  static const Color divider    = Color(0xFFE2E8F0);

  // Grade level colors
  static const Color dar  = Color(0xFF16A34A);
  static const Color aar  = Color(0xFF2563EB);
  static const Color paar = Color(0xFFD97706);
  static const Color naar = Color(0xFFDC2626);
}

ThemeData buildAppTheme() {
  final base = ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      primary: AppColors.primary,
      secondary: AppColors.gold,
      surface: AppColors.surface,
      error: AppColors.error,
      brightness: Brightness.light,
    ),
    useMaterial3: true,
  );

  return base.copyWith(
    textTheme: GoogleFonts.latoTextTheme(base.textTheme).copyWith(
      displayLarge: GoogleFonts.playfairDisplay(
        fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.primary,
      ),
      displayMedium: GoogleFonts.playfairDisplay(
        fontSize: 22, fontWeight: FontWeight.w600, color: AppColors.primary,
      ),
      titleLarge: GoogleFonts.lato(
        fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark,
      ),
      titleMedium: GoogleFonts.lato(
        fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textDark,
      ),
      bodyLarge: GoogleFonts.lato(fontSize: 15, color: AppColors.textDark),
      bodyMedium: GoogleFonts.lato(fontSize: 13, color: AppColors.textDark),
      labelSmall: GoogleFonts.lato(fontSize: 11, color: AppColors.textMuted),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: GoogleFonts.playfairDisplay(
        fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: GoogleFonts.lato(fontWeight: FontWeight.w700, fontSize: 14),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.divider),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.divider),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.divider),
      ),
      color: Colors.white,
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: Colors.white,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.textMuted,
      type: BottomNavigationBarType.fixed,
      elevation: 8,
    ),
    chipTheme: ChipThemeData(
      backgroundColor: AppColors.surface,
      labelStyle: GoogleFonts.lato(fontSize: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
    ),
    scaffoldBackgroundColor: AppColors.surface,
    dividerColor: AppColors.divider,
  );
}
