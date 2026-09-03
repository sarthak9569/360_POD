import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _tagNoController = TextEditingController();
  final MobileScannerController _scannerController = MobileScannerController();
  bool _isScanning = false;

  void _verifyAndProceed(String tagNo) {
    if (tagNo.isNotEmpty) {
      context.push('/subsidy/$tagNo');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid Tag Number')),
      );
    }
  }

  Future<void> _logout() async {
    await ApiService.logout();
    if (mounted) {
      context.go('/login');
    }
  }

  @override
  void dispose() {
    _tagNoController.dispose();
    _scannerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Partner Dashboard', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      drawer: Drawer(
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF4A00E0), Color(0xFF8E2DE2)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: ListView(
            padding: EdgeInsets.zero,
            children: [
              DrawerHeader(
                decoration: const BoxDecoration(color: Colors.transparent),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    const Icon(Icons.account_circle, size: 64, color: Colors.white),
                    const SizedBox(height: 12),
                    Text(
                      'District: ${ApiService.currentDistrict ?? "Unknown"}',
                      style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
              ListTile(
                leading: const Icon(Icons.qr_code_scanner, color: Colors.white),
                title: const Text('Scan QR', style: TextStyle(color: Colors.white, fontSize: 16)),
                onTap: () {
                  context.pop();
                },
              ),
              const Divider(color: Colors.white30, indent: 16, endIndent: 16),
              ListTile(
                leading: const Icon(Icons.logout, color: Colors.redAccent),
                title: const Text('Logout', style: TextStyle(color: Colors.redAccent, fontSize: 16, fontWeight: FontWeight.bold)),
                onTap: _logout,
              ),
            ],
          ),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF8E2DE2), Color(0xFF4A00E0)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Scan or Enter Code',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const SizedBox(height: 32),
                if (_isScanning)
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: [
                          BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 15, spreadRadius: 5),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(24),
                        child: MobileScanner(
                          controller: _scannerController,
                          onDetect: (capture) {
                            final List<Barcode> barcodes = capture.barcodes;
                            if (barcodes.isNotEmpty && barcodes.first.rawValue != null) {
                              final String code = barcodes.first.rawValue!;
                              setState(() {
                                _isScanning = false;
                              });
                              _scannerController.stop();
                              _verifyAndProceed(code);
                            }
                          },
                        ),
                      ),
                    ),
                  )
                else
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: Colors.white.withOpacity(0.2), width: 1.5),
                        boxShadow: [
                          BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 10, spreadRadius: 2),
                        ],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.qr_code_scanner, size: 100, color: Colors.white.withOpacity(0.8)),
                          const SizedBox(height: 24),
                          ElevatedButton.icon(
                            icon: const Icon(Icons.camera_alt, color: Color(0xFF4A00E0)),
                            label: const Text('Open Camera to Scan QR', style: TextStyle(color: Color(0xFF4A00E0), fontWeight: FontWeight.bold)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                              elevation: 5,
                            ),
                            onPressed: () {
                              setState(() {
                                _isScanning = true;
                              });
                              _scannerController.start();
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 32),
                Row(
                  children: [
                    Expanded(child: Divider(color: Colors.white.withOpacity(0.5))),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 16.0),
                      child: Text('OR', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w600)),
                    ),
                    Expanded(child: Divider(color: Colors.white.withOpacity(0.5))),
                  ],
                ),
                const SizedBox(height: 32),
                TextField(
                  controller: _tagNoController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'Enter Unique Code manually',
                    labelStyle: TextStyle(color: Colors.white.withOpacity(0.8)),
                    filled: true,
                    fillColor: Colors.white.withOpacity(0.1),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                      borderSide: BorderSide.none,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                      borderSide: const BorderSide(color: Colors.white, width: 1.5),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.tealAccent.shade400,
                    foregroundColor: Colors.black87,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    elevation: 5,
                  ),
                  onPressed: () {
                    _verifyAndProceed(_tagNoController.text.trim());
                  },
                  child: const Text('Submit Code', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
