import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
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
      final role = session['role'];
      if (role == 'admin') {
        context.go('/admin');
        return;
      } else {
        context.go('/home');
        return;
      }
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

  Future<void> _showAdminLoginDialog() async {
    final usernameController = TextEditingController();
    final passwordController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (dialogContext) {
        bool obscurePassword = true;
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Admin Login'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: usernameController,
                    decoration: const InputDecoration(labelText: 'Username'),
                  ),
                  TextField(
                    controller: passwordController,
                    obscureText: obscurePassword,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      suffixIcon: IconButton(
                        icon: Icon(obscurePassword ? Icons.visibility : Icons.visibility_off),
                        onPressed: () {
                          setState(() {
                            obscurePassword = !obscurePassword;
                          });
                        },
                      ),
                    ),
                  ),
                ],
              ),
              actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final uname = usernameController.text;
                final pwd = passwordController.text;
                try {
                  final response = await http.post(
                    Uri.parse('${ApiService.baseUrl}/admin/login'),
                    headers: {'Content-Type': 'application/json'},
                    body: jsonEncode({'username': uname, 'password': pwd}),
                  );
                  if (response.statusCode == 200) {
                    await ApiService.saveAdminSession();
                    if (dialogContext.mounted) {
                      Navigator.pop(dialogContext); // close dialog
                    }
                    if (mounted) {
                      context.go('/admin'); // goto admin
                    }
                  } else {
                    if (dialogContext.mounted) {
                      ScaffoldMessenger.of(dialogContext).showSnackBar(
                        const SnackBar(content: Text('Invalid credentials')),
                      );
                    }
                  }
                } catch (e) {
                  if (dialogContext.mounted) {
                    ScaffoldMessenger.of(dialogContext).showSnackBar(
                      SnackBar(content: Text('Error: $e')),
                    );
                  }
                }
              },
              child: const Text('Login'),
            )
          ],
        );
      },
      );
      },
    );
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
        title: const Text('Partner Login'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _fetchDistricts,
            tooltip: 'Refresh Districts',
          ),
          TextButton(
            onPressed: _showAdminLoginDialog,
            child: const Text('Admin', style: TextStyle(color: Colors.white)),
          )
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
                : const Text('Login', style: TextStyle(fontSize: 18)),
            ),
            const SizedBox(height: 16),
            TextButton(
              onPressed: _showAdminLoginDialog,
              child: const Text('Admin Dashboard Login', style: TextStyle(fontSize: 16, color: Colors.blueGrey)),
            ),
          ],
        ),
      ),
    );
  }
}
