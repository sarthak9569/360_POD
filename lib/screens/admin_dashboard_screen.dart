import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:go_router/go_router.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  List<dynamic> _beneficiaries = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchBeneficiaries();
  }

  Future<void> _fetchBeneficiaries() async {
    setState(() => _isLoading = true);
    try {
      final response = await http.get(Uri.parse('http://localhost:8000/api/beneficiaries'));
      if (response.statusCode == 200) {
        setState(() {
          _beneficiaries = jsonDecode(response.body);
        });
      }
    } catch (e) {
      debugPrint("Error fetching beneficiaries: $e");
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _deleteBeneficiary(String tagNo) async {
    try {
      final response = await http.delete(Uri.parse('http://localhost:8000/api/beneficiaries/$tagNo'));
      if (response.statusCode == 200) {
        _fetchBeneficiaries();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Deleted successfully')));
        }
      }
    } catch (e) {
      debugPrint("Error deleting beneficiary: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Beneficiaries Dashboard'),
        backgroundColor: Colors.blueGrey,
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _beneficiaries.isEmpty
              ? const Center(child: Text("No beneficiaries found."))
              : ListView.builder(
                  itemCount: _beneficiaries.length,
                  itemBuilder: (context, index) {
                    final b = _beneficiaries[index];
                    return Card(
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: ListTile(
                        leading: const CircleAvatar(
                          backgroundColor: Colors.blueGrey,
                          child: Icon(Icons.person, color: Colors.white),
                        ),
                        title: Text('${b['farmer_name']} - ${b['tag_no']}'),
                        subtitle: Text('Village: ${b['village']} | Cattle Feed: ${b['cattle_feed_kg']}kg, Silage: ${b['silage_kg']}kg'),
                        trailing: IconButton(
                          icon: const Icon(Icons.delete, color: Colors.red),
                          onPressed: () {
                            showDialog(
                              context: context,
                              builder: (context) => AlertDialog(
                                title: const Text('Delete Beneficiary'),
                                content: Text('Are you sure you want to delete ${b['farmer_name']}?'),
                                actions: [
                                  TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                                  ElevatedButton(
                                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
                                    onPressed: () {
                                      Navigator.pop(context);
                                      _deleteBeneficiary(b['tag_no']);
                                    },
                                    child: const Text('Delete'),
                                  )
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await context.push('/admin/add');
          _fetchBeneficiaries(); // Refresh when back
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
