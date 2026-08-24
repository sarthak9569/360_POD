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
            final summary = data["summary"] ?? {};
            final imported = summary["Successfully imported"] ?? 0;
            final skipped = summary["Skipped rows"] ?? 0;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Upload complete: $imported inserted, $skipped skipped')),
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
      backgroundColor: const Color(0xFF0D1117), // Deep Dark Background
      appBar: AppBar(
        title: const Text('SECURE ZONE // ADMIN', style: TextStyle(fontFamily: 'Courier', fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        backgroundColor: const Color(0xFF161B22), // Darker App Bar
        foregroundColor: Colors.greenAccent, // Neon Accent
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.upload_file, color: Colors.greenAccent),
            tooltip: 'Upload Excel',
            onPressed: _uploadExcel,
          ),
          IconButton(
            icon: const Icon(Icons.qr_code_2, color: Colors.greenAccent),
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
        backgroundColor: const Color(0xFF161B22),
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(
                color: Color(0xFF0D1117),
                border: Border(bottom: BorderSide(color: Colors.greenAccent, width: 2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Icon(Icons.security, size: 50, color: Colors.greenAccent),
                  SizedBox(height: 10),
                  Text(
                    'ADMIN ACCESS',
                    style: TextStyle(color: Colors.greenAccent, fontSize: 20, fontFamily: 'Courier', fontWeight: FontWeight.bold, letterSpacing: 2),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.people_outline, color: Colors.white70),
              title: const Text('Beneficiaries', style: TextStyle(color: Colors.white70, fontFamily: 'Courier')),
              onTap: () {
                context.pop(); // close drawer
              },
            ),
            ListTile(
              leading: const Icon(Icons.admin_panel_settings, color: Colors.white70),
              title: const Text('Supervisors', style: TextStyle(color: Colors.white70, fontFamily: 'Courier')),
              onTap: () {
                context.pop();
                context.push('/admin/supervisors');
              },
            ),
            const Divider(color: Colors.white24, indent: 16, endIndent: 16),
            ListTile(
              leading: const Icon(Icons.power_settings_new, color: Colors.redAccent),
              title: const Text('LOGOUT', style: TextStyle(color: Colors.redAccent, fontFamily: 'Courier', fontWeight: FontWeight.bold, letterSpacing: 2)),
              onTap: () {
                ApiService.logout();
                context.go('/login');
              },
            ),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.greenAccent))
          : Column(
              children: [
                Container(
                  color: const Color(0xFF161B22),
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: TextField(
                          style: const TextStyle(color: Colors.greenAccent, fontFamily: 'Courier'),
                          decoration: InputDecoration(
                            hintText: 'Search Name, Tag...',
                            hintStyle: TextStyle(color: Colors.greenAccent.withOpacity(0.5), fontFamily: 'Courier'),
                            prefixIcon: const Icon(Icons.search, color: Colors.greenAccent),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(4.0),
                              borderSide: BorderSide(color: Colors.greenAccent.withOpacity(0.3)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(4.0),
                              borderSide: const BorderSide(color: Colors.greenAccent),
                            ),
                            filled: true,
                            fillColor: const Color(0xFF0D1117),
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
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0D1117),
                            border: Border.all(color: Colors.greenAccent.withOpacity(0.3)),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              dropdownColor: const Color(0xFF161B22),
                              isExpanded: true,
                              icon: const Icon(Icons.arrow_drop_down, color: Colors.greenAccent),
                              style: const TextStyle(color: Colors.greenAccent, fontFamily: 'Courier'),
                              value: _selectedDistrict ?? 'All Districts',
                              items: _districts.map((d) => DropdownMenuItem(value: d, child: Text(d, overflow: TextOverflow.ellipsis))).toList(),
                              onChanged: (value) {
                                _selectedDistrict = value;
                                _applyFilters();
                              },
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _filteredBeneficiaries.isEmpty
                      ? const Center(child: Text("NO DATA FOUND", style: TextStyle(color: Colors.redAccent, fontFamily: 'Courier', letterSpacing: 2)))
                      : ListView.builder(
                          itemCount: _filteredBeneficiaries.length,
                          itemBuilder: (context, index) {
                            final b = _filteredBeneficiaries[index];
                            return Card(
                              color: const Color(0xFF161B22),
                              shape: RoundedRectangleBorder(
                                side: BorderSide(color: Colors.greenAccent.withOpacity(0.2)),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              child: ListTile(
                                leading: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    IconButton(
                                      icon: const Icon(Icons.qr_code_2, color: Colors.greenAccent),
                                      tooltip: 'Download QR',
                                      onPressed: () async {
                                        final url = Uri.parse('${ApiService.baseUrl}/beneficiaries/${b['tag_no']}/qrs/download');
                                        try {
                                          await launchUrl(url, mode: LaunchMode.externalApplication);
                                        } catch (e) {
                                          if (context.mounted) {
                                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
                                          }
                                        }
                                      },
                                    ),
                                    const CircleAvatar(
                                      backgroundColor: Color(0xFF0D1117),
                                      child: Icon(Icons.person, color: Colors.greenAccent),
                                    ),
                                  ],
                                ),
                                title: Text('${b['farmer_name']} - ${b['tag_no']}', style: const TextStyle(color: Colors.white, fontFamily: 'Courier', fontWeight: FontWeight.bold)),
                                subtitle: Text('Village: ${b['village']}\nFeed: ${b['cattle_feed_kg']}kg | Silage: ${b['silage_kg']}kg', style: const TextStyle(color: Colors.white70, fontFamily: 'Courier')),
                                isThreeLine: true,
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_forever, color: Colors.redAccent),
                                  onPressed: () {
                                    showDialog(
                                      context: context,
                                      builder: (context) => AlertDialog(
                                        backgroundColor: const Color(0xFF161B22),
                                        title: const Text('WARNING: DELETION', style: TextStyle(color: Colors.redAccent, fontFamily: 'Courier', fontWeight: FontWeight.bold)),
                                        content: Text('PURGE ${b['farmer_name']} FROM DATABASE?', style: const TextStyle(color: Colors.white70, fontFamily: 'Courier')),
                                        actions: [
                                          TextButton(onPressed: () => Navigator.pop(context), child: const Text('ABORT', style: TextStyle(color: Colors.greenAccent, fontFamily: 'Courier'))),
                                          ElevatedButton(
                                            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent, foregroundColor: Colors.black),
                                            onPressed: () {
                                              Navigator.pop(context);
                                              _deleteBeneficiary(b['tag_no']);
                                            },
                                            child: const Text('PURGE', style: TextStyle(fontFamily: 'Courier', fontWeight: FontWeight.bold)),
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
        backgroundColor: Colors.greenAccent,
        foregroundColor: Colors.black,
        onPressed: () async {
          await context.push('/admin/add');
          _fetchBeneficiaries(); // Refresh when back
        },
        child: const Icon(Icons.add_moderator),
      ),
    );
  }
}
