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
  String? selectedVillage;
  final TextEditingController _partnerNameController = TextEditingController();

  // Mock list for now. This could be fetched from the backend.
  final List<String> villages = [
    'Ghodagaon',
    'Dhoragaon',
    'Masra',
    'Alor',
    'Belmala',
    'Sharda Nagar',
    'Bade Kapsi',
    'Ghotiya',
    'Aja',
    'Dhanagahan',
    'Janki Nagar',
    'Harsngarh'
  ];

  Future<void> _showAdminLoginDialog() async {
    final usernameController = TextEditingController();
    final passwordController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (dialogContext) {
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
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password'),
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
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Partner Login'),
        actions: [
          TextButton(
            onPressed: _showAdminLoginDialog,
            child: const Text('Admin', style: TextStyle(color: Colors.white)),
          )
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.local_shipping, size: 100, color: Colors.green),
            const SizedBox(height: 32),
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Select Village',
                border: OutlineInputBorder(),
              ),
              initialValue: selectedVillage,
              items: villages.map((String village) {
                return DropdownMenuItem<String>(
                  value: village,
                  child: Text(village),
                );
              }).toList(),
              onChanged: (String? newValue) {
                setState(() {
                  selectedVillage = newValue;
                });
              },
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _partnerNameController,
              decoration: const InputDecoration(
                labelText: 'Delivery Partner Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              onPressed: () {
                if (selectedVillage != null && _partnerNameController.text.isNotEmpty) {
                  // In a real app, you might save this in local storage/state
                  context.go('/home');
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Please fill all fields')),
                  );
                }
              },
              child: const Text('Login', style: TextStyle(fontSize: 18)),
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
