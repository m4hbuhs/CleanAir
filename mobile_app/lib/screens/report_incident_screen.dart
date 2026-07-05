import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:record/record.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../services/api_service.dart';

class ReportIncidentScreen extends StatefulWidget {
  const ReportIncidentScreen({super.key});

  @override
  _ReportIncidentScreenState createState() => _ReportIncidentScreenState();
}

class _ReportIncidentScreenState extends State<ReportIncidentScreen> with SingleTickerProviderStateMixin {
  final ApiService _apiService = ApiService();
  final ImagePicker _picker = ImagePicker();
  final AudioRecorder _audioRecorder = AudioRecorder();

  File? _imageFile;
  File? _audioFile;
  bool _isRecording = false;
  bool _isSubmitting = false;
  String _activeCategory = 'Garbage Burning';
  String _liveMetadata = 'Ready.';

  // Animation controller for the Walkie-Talkie pulse
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  final List<String> _categories = [
    'Garbage Burning',
    'Industrial Plume',
    'Road Dust',
    'Vehicular Congestion',
    'Other'
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  Future<void> _captureImage() async {
    try {
      setState(() => _liveMetadata = 'Opening Camera...');
      final XFile? photo = await _picker.pickImage(source: ImageSource.camera);
      if (photo != null) {
        setState(() {
          _imageFile = File(photo.path);
          _liveMetadata = 'EXIF: Captured | Ready for Upload';
        });
        _showSnackBar('Photo attached successfully.', Colors.tealAccent);
      } else {
        setState(() => _liveMetadata = 'Camera aborted.');
      }
    } catch (e) {
      _showSnackBar('Camera unavailable (Check permissions or running on Web).', Colors.redAccent);
      setState(() => _liveMetadata = 'Error: Camera Unavailable');
    }
  }

  Future<void> _startRecording() async {
    try {
      if (kIsWeb) {
        _showSnackBar('Audio recording is limited on Web MVP.', Colors.orangeAccent);
        return;
      }
      if (await _audioRecorder.hasPermission()) {
        final directory = Directory.systemTemp;
        final path = '${directory.path}/voice_note_${DateTime.now().millisecondsSinceEpoch}.m4a';
        
        await _audioRecorder.start(
          const RecordConfig(encoder: AudioEncoder.aacLc), 
          path: path
        );
        
        setState(() {
          _isRecording = true;
          _liveMetadata = 'Recording audio...';
        });
        _pulseController.repeat(reverse: true);
      }
    } catch (e) {
      _showSnackBar('Microphone error.', Colors.redAccent);
    }
  }

  Future<void> _stopRecording() async {
    if (kIsWeb) return;
    try {
      final path = await _audioRecorder.stop();
      _pulseController.stop();
      _pulseController.reset();

      if (path != null) {
        setState(() {
          _isRecording = false;
          _audioFile = File(path);
          _liveMetadata = 'Audio footprint cached.';
        });
        _showSnackBar('Voice note recorded.', Colors.tealAccent);
      }
    } catch (e) {
      setState(() => _isRecording = false);
    }
  }

  Future<void> _submitReport() async {
    if (_imageFile == null && _audioFile == null && !kIsWeb) {
      _showSnackBar('Please add a photo or voice note.', Colors.orangeAccent);
      return;
    }

    setState(() {
      _isSubmitting = true;
      _liveMetadata = 'Harvesting GPS coordinates...';
    });

    try {
      Position? position;
      if (kIsWeb) {
        // Mock position for web testing where geolocation can fail or require HTTPS
        position = Position(
          latitude: 28.6364, longitude: 77.2010, timestamp: DateTime.now(), 
          accuracy: 1.0, altitude: 0, heading: 0, speed: 0, speedAccuracy: 0, 
          altitudeAccuracy: 0, headingAccuracy: 0
        );
      } else {
        LocationPermission permission = await Geolocator.checkPermission();
        if (permission == LocationPermission.denied) {
          permission = await Geolocator.requestPermission();
        }
        if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
          position = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
        } else {
          throw Exception('Location denied');
        }
      }

      setState(() => _liveMetadata = 'Transmitting Multi-Modal Payload...');

      bool success = await _apiService.submitIncidentReport(
        location: position,
        imageFile: _imageFile,
        audioFile: _audioFile,
        category: _activeCategory,
      );

      if (success) {
        _showSnackBar('Incident Logged Successfully.', Colors.tealAccent);
        setState(() {
          _imageFile = null;
          _audioFile = null;
          _liveMetadata = 'Payload delivered to command center.';
        });
      } else {
        _showSnackBar('Submission failed.', Colors.redAccent);
        setState(() => _liveMetadata = 'Network routing failed.');
      }
    } catch (e) {
      _showSnackBar('Transmission Error: $e', Colors.redAccent);
      setState(() => _liveMetadata = 'Critical System Error');
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  void _showSnackBar(String message, Color color) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message, style: const TextStyle(color: Colors.black)),
        backgroundColor: color,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[900], // Premium Dark Theme
      appBar: AppBar(
        title: const Text('Field Reporting Node', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: Colors.black87,
        elevation: 0,
        centerTitle: true,
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Category Selectors Row
            Container(
              height: 80,
              padding: const EdgeInsets.symmetric(vertical: 16),
              color: Colors.black87,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: _categories.length,
                itemBuilder: (context, index) {
                  final cat = _categories[index];
                  final isActive = _activeCategory == cat;
                  return Padding(
                    padding: const EdgeInsets.only(right: 12.0),
                    child: ChoiceChip(
                      label: Text(cat, style: TextStyle(
                        color: isActive ? Colors.black : Colors.white70,
                        fontWeight: isActive ? FontWeight.bold : FontWeight.normal
                      )),
                      selected: isActive,
                      onSelected: (selected) {
                        if (selected) setState(() => _activeCategory = cat);
                      },
                      selectedColor: Colors.tealAccent,
                      backgroundColor: Colors.grey[850],
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    ),
                  );
                },
              ),
            ),
            
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Glassmorphic Camera Button
                    GestureDetector(
                      onTap: _captureImage,
                      child: Container(
                        height: 120,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: _imageFile == null ? Colors.white.withValues(alpha: 0.05) : Colors.teal.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(color: _imageFile == null ? Colors.white12 : Colors.tealAccent.withValues(alpha: 0.5)),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.camera_alt_outlined, size: 48, color: _imageFile == null ? Colors.white54 : Colors.tealAccent),
                            const SizedBox(height: 12),
                            Text(
                              _imageFile == null ? 'Capture Physical Evidence' : 'Evidence Attached',
                              style: TextStyle(color: _imageFile == null ? Colors.white54 : Colors.tealAccent, fontSize: 16),
                            )
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Animated Walkie-Talkie UX
                    GestureDetector(
                      onLongPressStart: (_) => _startRecording(),
                      onLongPressEnd: (_) => _stopRecording(),
                      child: ScaleTransition(
                        scale: _pulseAnimation,
                        child: Container(
                          height: 180,
                          width: double.infinity,
                          decoration: BoxDecoration(
                            color: _isRecording ? Colors.redAccent.withValues(alpha: 0.2) : Colors.white.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(32),
                            border: Border.all(
                              color: _isRecording ? Colors.redAccent : Colors.white12,
                              width: _isRecording ? 2 : 1
                            ),
                            boxShadow: [
                              if (_isRecording)
                                BoxShadow(color: Colors.redAccent.withValues(alpha: 0.4), blurRadius: 30, spreadRadius: 5)
                            ]
                          ),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                _isRecording ? Icons.mic : Icons.mic_none, 
                                size: 64, 
                                color: _isRecording ? Colors.redAccent : Colors.white54
                              ),
                              const SizedBox(height: 16),
                              Text(
                                _isRecording ? 'TRANSMITTING...' : 'HOLD TO SPEAK',
                                style: TextStyle(
                                  fontSize: 16, 
                                  color: _isRecording ? Colors.redAccent : Colors.white54, 
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 2
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const Spacer(),

                    // Live Metadata Panel
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.black45,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white10)
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.satellite_alt, color: Colors.tealAccent, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _liveMetadata,
                              style: const TextStyle(color: Colors.tealAccent, fontFamily: 'monospace', fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Submission Action
                    SizedBox(
                      width: double.infinity,
                      height: 60,
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : _submitReport,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.tealAccent,
                          foregroundColor: Colors.black,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          elevation: 0,
                        ),
                        child: _isSubmitting
                            ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2))
                            : const Text('INITIATE UPLOAD', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
