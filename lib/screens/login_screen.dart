import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  String? selectedDistrict;
  String? selectedVillage;
  final TextEditingController _supervisorNameController = TextEditingController();
  final TextEditingController _partnerNameController = TextEditingController();

  List<String> districts = [];
  List<String> villages = [];
  bool isLoadingDistricts = true;
  bool isLoadingVillages = false;
  bool isLoggingIn = false;

  bool _isCheckingSession = true;

  @override
  void initState() {
    super.initState();
    _checkSavedSession();
  }

  Future<void> _checkSavedSession() async {
    final session = await ApiService.getSavedSession();
    if (session != null && mounted) {
      context.go('/home');
      return;
    }
    if (mounted) {
      setState(() {
        _isCheckingSession = false;
      });
      _fetchDistricts();
    }
  }

  Future<void> _fetchDistricts() async {
    setState(() {
      isLoadingDistricts = true;
    });
    final fetchedDistricts = await ApiService.getDistricts();
    if (mounted) {
      setState(() {
        districts = fetchedDistricts;
        isLoadingDistricts = false;
        if (selectedDistrict != null && !districts.contains(selectedDistrict)) {
          selectedDistrict = null;
          selectedVillage = null;
          villages = [];
        }
      });
    }
  }

  Future<void> _fetchVillages(String district) async {
    setState(() {
      isLoadingVillages = true;
      selectedVillage = null;
      villages = [];
    });
    final fetchedVillages = await ApiService.getVillages(district);
    if (mounted) {
      setState(() {
        villages = fetchedVillages;
        isLoadingVillages = false;
      });
    }
  }

  Future<void> _handlePartnerLogin() async {
    if (selectedDistrict == null || selectedVillage == null || _supervisorNameController.text.isEmpty || _partnerNameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please fill all fields')));
      return;
    }

    setState(() => isLoggingIn = true);

    final success = await ApiService.partnerLogin(
      district: selectedDistrict!,
      village: selectedVillage!,
      supervisorName: _supervisorNameController.text.trim(),
      partnerName: _partnerNameController.text.trim(),
    );

    if (mounted) {
      setState(() => isLoggingIn = false);
      if (success) {
        await ApiService.savePartnerSession(
          district: selectedDistrict!,
          village: selectedVillage!,
          supervisorName: _supervisorNameController.text.trim(),
          partnerName: _partnerNameController.text.trim(),
        );
        if (mounted) {
          context.go('/home');
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Login failed: Invalid supervisor name for the selected district.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isCheckingSession) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Supervisor Login'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _fetchDistricts,
            tooltip: 'Refresh Districts',
          ),
          TextButton.icon(
            icon: const Icon(Icons.admin_panel_settings_outlined, color: Colors.white70, size: 18),
            label: const Text('Admin', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold)),
            onPressed: () => context.push('/admin'),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 40),
            const Icon(Icons.local_shipping, size: 100, color: Colors.green),
            const SizedBox(height: 32),
            if (isLoadingDistricts)
              const Center(child: CircularProgressIndicator())
            else
              DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  labelText: 'Select District',
                  border: OutlineInputBorder(),
                ),
                value: selectedDistrict,
                items: districts.map((String district) {
                  return DropdownMenuItem<String>(
                    value: district,
                    child: Text(district),
                  );
                }).toList(),
                onChanged: (String? newValue) {
                  if (newValue != null) {
                    setState(() {
                      selectedDistrict = newValue;
                    });
                    _fetchVillages(newValue);
                  }
                },
              ),
            const SizedBox(height: 16),
            if (isLoadingVillages)
              const Center(child: CircularProgressIndicator())
            else
              DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  labelText: 'Select Village',
                  border: OutlineInputBorder(),
                ),
                value: selectedVillage,
                items: villages.map((String village) {
                  return DropdownMenuItem<String>(
                    value: village,
                    child: Text(village),
                  );
                }).toList(),
                onChanged: selectedDistrict == null ? null : (String? newValue) {
                  setState(() {
                    selectedVillage = newValue;
                  });
                },
              ),
            const SizedBox(height: 16),
            TextField(
              controller: _partnerNameController,
              decoration: const InputDecoration(
                labelText: 'Partner Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _supervisorNameController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Supervisor Name (Password)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              onPressed: isLoggingIn ? null : _handlePartnerLogin,
              child: isLoggingIn 
                ? const CircularProgressIndicator(color: Colors.white)
                : const Text('Login as Supervisor', style: TextStyle(fontSize: 18)),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              icon: const Icon(Icons.admin_panel_settings_rounded, color: Color(0xFF0284C7)),
              label: const Text('Open 360 Parenting Admin Dashboard', style: TextStyle(color: Color(0xFF0284C7), fontWeight: FontWeight.bold)),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                side: const BorderSide(color: Color(0xFF0284C7)),
              ),
              onPressed: () => context.push('/admin'),
            ),
          ],
        ),
      ),
    );
  }
}
