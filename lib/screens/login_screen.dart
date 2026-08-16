import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Partner Login'),
        actions: [
          TextButton(
            onPressed: () {
              context.go('/admin');
            },
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
          ],
        ),
      ),
    );
  }
}
