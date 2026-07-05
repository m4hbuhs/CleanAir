import 'package:flutter/material.dart';
import 'screens/report_incident_screen.dart';

void main() {
  runApp(const CleanAirApp());
}

class CleanAirApp extends StatelessWidget {
  const CleanAirApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CleanAir Citizen Reporter',
      theme: ThemeData(
        primarySwatch: Colors.green,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: const ReportIncidentScreen(),
    );
  }
}
