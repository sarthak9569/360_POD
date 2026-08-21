import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:file_picker/file_picker.dart';
import '../services/api_service.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  List<dynamic> _beneficiaries = [];
  List<dynamic> _filteredBeneficiaries = [];
  bool _isLoading = true;

  String _searchQuery = '';
  String? _selectedDistrict;

  @override
  void initState() {
    super.initState();
    _fetchBeneficiaries();
  }

  Future<void> _fetchBeneficiaries() async {
    setState(() => _isLoading = true);
    try {
      final response = await http.get(Uri.parse('${ApiService.baseUrl}/beneficiaries'));
      if (response.statusCode == 200) {
        setState(() {
          _beneficiaries = jsonDecode(response.body);
          _applyFilters();
        });
      }
    } catch (e) {
      debugPrint("Error fetching beneficiaries: $e");
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _applyFilters() {
    setState(() {
      _filteredBeneficiaries = _beneficiaries.where((b) {
        final farmerName = (b['farmer_name'] ?? '').toString().toLowerCase();
        final village = (b['village'] ?? '').toString().toLowerCase();
        final tagNo = (b['tag_no'] ?? '').toString().toLowerCase();
        final district = (b['district'] ?? '').toString();
        
        final matchesSearch = _searchQuery.isEmpty || 
                              farmerName.contains(_searchQuery.toLowerCase()) || 
                              village.contains(_searchQuery.toLowerCase()) || 
                              tagNo.contains(_searchQuery.toLowerCase());
        
        final matchesDistrict = _selectedDistrict == null || _selectedDistrict == 'All Districts' || district == _selectedDistrict;
        
        return matchesSearch && matchesDistrict;
      }).toList();
    });
  }

  List<String> get _districts {
    final districts = _beneficiaries
        .map((b) => (b['district'] ?? '').toString())
        .where((d) => d.isNotEmpty)
        .toSet()
        .toList();
    districts.sort();
    return ['All Districts', ...districts];
  }

  Future<void> _deleteBeneficiary(String tagNo) async {
    try {
      final response = await http.delete(Uri.parse('${ApiService.baseUrl}/beneficiaries/$tagNo'));
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

  Future<void> _uploadExcel() async {
    try {
      PlatformFile? result = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['xlsx', 'xls'],
      );

      if (result != null && result.path != null) {
        setState(() => _isLoading = true);
        var request = http.MultipartRequest('POST', Uri.parse('${ApiService.baseUrl}/beneficiaries/upload'));
        request.files.add(await http.MultipartFile.fromPath('file', result.path!));
        
        var response = await request.send();
        if (response.statusCode == 200) {
          final respStr = await response.stream.bytesToString();
          final data = jsonDecode(respStr);
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Upload complete: ${data["inserted"]} inserted, ${data["skipped"]} skipped')),
            );
          }
          _fetchBeneficiaries();
        } else {
          final respStr = await response.stream.bytesToString();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Upload failed (${response.statusCode}): $respStr')),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error uploading: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Beneficiaries Dashboard'),
        backgroundColor: Colors.blueGrey,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.upload_file),
            tooltip: 'Upload Excel',
            onPressed: _uploadExcel,
          ),
          IconButton(
            icon: const Icon(Icons.qr_code_2),
            tooltip: 'Download All QRs',
            onPressed: () async {
              final url = Uri.parse('${ApiService.baseUrl}/beneficiaries/qrs/download');
              try {
                await launchUrl(url, mode: LaunchMode.externalApplication);
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not launch download URL: $e')));
                }
              }
            },
          ),
        ],
      ),
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(
                color: Colors.blueGrey,
              ),
              child: Text(
                'Admin Menu',
                style: TextStyle(color: Colors.white, fontSize: 24),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.people),
              title: const Text('Beneficiaries'),
              onTap: () {
                context.pop(); // close drawer
              },
            ),
            ListTile(
              leading: const Icon(Icons.admin_panel_settings),
              title: const Text('Supervisors'),
              onTap: () {
                context.pop();
                context.push('/admin/supervisors');
              },
            ),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: TextField(
                          decoration: InputDecoration(
                            hintText: 'Search Name, Village, Tag...',
                            prefixIcon: const Icon(Icons.search),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          onChanged: (value) {
                            _searchQuery = value;
                            _applyFilters();
                          },
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        flex: 1,
                        child: DropdownButton<String>(
                          isExpanded: true,
                          value: _selectedDistrict ?? 'All Districts',
                          items: _districts.map((d) => DropdownMenuItem(value: d, child: Text(d, overflow: TextOverflow.ellipsis))).toList(),
                          onChanged: (value) {
                            _selectedDistrict = value;
                            _applyFilters();
                          },
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _filteredBeneficiaries.isEmpty
                      ? const Center(child: Text("No beneficiaries found."))
                      : ListView.builder(
                          itemCount: _filteredBeneficiaries.length,
                          itemBuilder: (context, index) {
                            final b = _filteredBeneficiaries[index];
                            return Card(
                              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: ListTile(
                        leading: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.qr_code_2, color: Colors.blue),
                              tooltip: 'Download QR',
                              onPressed: () async {
                                final url = Uri.parse('${ApiService.baseUrl}/beneficiaries/${b['tag_no']}/qrs/download');
                                try {
                                  await launchUrl(url, mode: LaunchMode.externalApplication);
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not launch download URL: $e')));
                                  }
                                }
                              },
                            ),
                            const CircleAvatar(
                              backgroundColor: Colors.blueGrey,
                              child: Icon(Icons.person, color: Colors.white),
                            ),
                          ],
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
                ),
              ],
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
