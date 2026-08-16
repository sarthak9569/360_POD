import 'package:flutter/material.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  // Mock data for deliveries
  final List<Map<String, dynamic>> _deliveries = [
    {
      'tagNo': '106208111223',
      'farmerName': 'Dashri Potai',
      'village': 'Ghodagaon',
      'status': 'delivered',
      'partnerName': 'John Doe'
    },
    {
      'tagNo': '106296833111',
      'farmerName': 'Dashri Potai',
      'village': 'Ghodagaon',
      'status': 'pending',
      'partnerName': ''
    },
    {
      'tagNo': '106296201654',
      'farmerName': 'Ogarn Gawde',
      'village': 'Dhoragaon',
      'status': 'pending',
      'partnerName': ''
    },
  ];

  void _updateStatus(int index, String newStatus) {
    // Call backend API to update status here
    setState(() {
      _deliveries[index]['status'] = newStatus;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Dashboard'),
        backgroundColor: Colors.blueGrey,
        foregroundColor: Colors.white,
      ),
      body: _deliveries.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _deliveries.length,
              itemBuilder: (context, index) {
                final delivery = _deliveries[index];
                final bool isDelivered = delivery['status'] == 'delivered';

                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: isDelivered ? Colors.green : Colors.orange,
                      child: Icon(isDelivered ? Icons.check : Icons.pending, color: Colors.white),
                    ),
                    title: Text('${delivery['farmerName']} - ${delivery['tagNo']}'),
                    subtitle: Text('Village: ${delivery['village']} | Partner: ${delivery['partnerName'].isEmpty ? 'N/A' : delivery['partnerName']}'),
                    trailing: DropdownButton<String>(
                      value: delivery['status'],
                      items: const [
                        DropdownMenuItem(value: 'pending', child: Text('Pending')),
                        DropdownMenuItem(value: 'delivered', child: Text('Delivered')),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          _updateStatus(index, value);
                        }
                      },
                    ),
                  ),
                );
              },
            ),
    );
  }
}
