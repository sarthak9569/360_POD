import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';

class SupervisorManagementScreen extends StatefulWidget {
  const SupervisorManagementScreen({super.key});

  @override
  State<SupervisorManagementScreen> createState() => _SupervisorManagementScreenState();
}

class _SupervisorManagementScreenState extends State<SupervisorManagementScreen> {
  List<dynamic> _supervisors = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchSupervisors();
  }

  Future<void> _fetchSupervisors() async {
    setState(() => _isLoading = true);
    final supervisors = await ApiService.getSupervisors();
    if (mounted) {
      setState(() {
        _supervisors = supervisors;
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteSupervisor(String id, String name) async {
    final success = await ApiService.deleteSupervisor(id);
    if (success) {
      _fetchSupervisors();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Deleted $name')));
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Failed to delete')));
      }
    }
  }

  void _showSupervisorDialog({Map<String, dynamic>? supervisor}) {
    final isEditing = supervisor != null;
    final nameController = TextEditingController(text: isEditing ? supervisor['name'] : '');
    
    // Convert lists back to comma-separated strings for easy editing
    final districtsList = isEditing ? (supervisor['districts'] as List<dynamic>).join(', ') : '';
    final villagesList = isEditing ? (supervisor['villages'] as List<dynamic>).join(', ') : '';
    
    final districtsController = TextEditingController(text: districtsList);
    final villagesController = TextEditingController(text: villagesList);

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(isEditing ? 'Edit Supervisor' : 'Add Supervisor'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Name'),
                ),
                TextField(
                  controller: districtsController,
                  decoration: const InputDecoration(
                    labelText: 'Districts',
                    hintText: 'Comma separated (e.g. Kanker, Kondagaon)',
                  ),
                ),
                TextField(
                  controller: villagesController,
                  decoration: const InputDecoration(
                    labelText: 'Villages',
                    hintText: 'Comma separated',
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final name = nameController.text.trim();
                final districts = districtsController.text
                    .split(',')
                    .map((e) => e.trim())
                    .where((e) => e.isNotEmpty)
                    .toList();
                final villages = villagesController.text
                    .split(',')
                    .map((e) => e.trim())
                    .where((e) => e.isNotEmpty)
                    .toList();

                if (name.isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Name is required')));
                  return;
                }

                Navigator.pop(context);
                setState(() => _isLoading = true);

                bool success;
                if (isEditing) {
                  success = await ApiService.updateSupervisor(
                    id: supervisor['_id'],
                    name: name,
                    districts: districts,
                    villages: villages,
                  );
                } else {
                  success = await ApiService.createSupervisor(
                    name: name,
                    districts: districts,
                    villages: villages,
                  );
                }

                if (success) {
                  _fetchSupervisors();
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(isEditing ? 'Updated successfully' : 'Added successfully')),
                    );
                  }
                } else {
                  if (mounted) {
                    setState(() => _isLoading = false);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Failed to save supervisor')),
                    );
                  }
                }
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Manage Supervisors'),
        backgroundColor: Colors.blueGrey,
        foregroundColor: Colors.white,
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
                context.go('/admin'); // Assuming /admin is the beneficiaries dashboard
              },
            ),
            ListTile(
              leading: const Icon(Icons.admin_panel_settings),
              title: const Text('Supervisors'),
              onTap: () {
                context.pop();
              },
            ),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _supervisors.isEmpty
              ? const Center(child: Text("No supervisors found."))
              : ListView.builder(
                  itemCount: _supervisors.length,
                  itemBuilder: (context, index) {
                    final s = _supervisors[index];
                    final districtsStr = (s['districts'] as List<dynamic>).join(', ');
                    final villagesStr = (s['villages'] as List<dynamic>).join(', ');

                    return Card(
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: ListTile(
                        leading: const CircleAvatar(
                          backgroundColor: Colors.indigo,
                          child: Icon(Icons.person, color: Colors.white),
                        ),
                        title: Text(s['name']),
                        subtitle: Text('Districts: $districtsStr\nVillages: $villagesStr'),
                        isThreeLine: true,
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit, color: Colors.blue),
                              onPressed: () => _showSupervisorDialog(supervisor: s),
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete, color: Colors.red),
                              onPressed: () {
                                showDialog(
                                  context: context,
                                  builder: (context) => AlertDialog(
                                    title: const Text('Delete Supervisor'),
                                    content: Text('Are you sure you want to delete ${s['name']}?'),
                                    actions: [
                                      TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                                      ElevatedButton(
                                        style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
                                        onPressed: () {
                                          Navigator.pop(context);
                                          _deleteSupervisor(s['_id'], s['name']);
                                        },
                                        child: const Text('Delete'),
                                      )
                                    ],
                                  ),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showSupervisorDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
