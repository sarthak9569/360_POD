import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class InvoiceScreen extends StatelessWidget {
  final String tagNo;
  InvoiceScreen({super.key, required this.tagNo});

  // Mock data. In real app, fetch this from backend using tagNo
  final Map<String, dynamic> invoiceData = {
    'farmerName': 'Dashri Potai',
    'address': 'Ghodagaon, Kanker',
    'items': [
      {'name': 'Cattle Feed', 'quantity': '22 kg'},
      {'name': 'Silage', 'quantity': '55 kg'},
    ],
    'partnerName': 'John Doe',
    'date': '2026-08-16',
    // In a real app, these would be URLs from Cloudinary
    'partnerPhoto': 'https://via.placeholder.com/150',
    'receiverPhoto': 'https://via.placeholder.com/150',
    'itemsPhoto': 'https://via.placeholder.com/150',
    'pdfUrl': 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
  };

  Future<void> _downloadPdf(BuildContext context) async {
    final Uri url = Uri.parse(invoiceData['pdfUrl']);
    if (!await launchUrl(url)) {
      if(context.mounted) {
         ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not launch PDF')),
         );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Invoice Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: () => _downloadPdf(context),
            tooltip: 'Download PDF',
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Center(
                  child: Text(
                    'INVOICE',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, letterSpacing: 2),
                  ),
                ),
                const Divider(height: 32, thickness: 2),
                Text('Date: ${invoiceData['date']}'),
                Text('Tag Number: $tagNo'),
                Text('Delivered By: ${invoiceData['partnerName']}'),
                const SizedBox(height: 16),
                const Text('Receiver Details:', style: TextStyle(fontWeight: FontWeight.bold)),
                Text('Name: ${invoiceData['farmerName']}'),
                Text('Address: ${invoiceData['address']}'),
                const Divider(height: 32),
                const Text('Items Delivered:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 8),
                ...List.generate(invoiceData['items'].length, (index) {
                  final item = invoiceData['items'][index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(item['name']),
                        Text(item['quantity'], style: const TextStyle(fontWeight: FontWeight.bold)),
                      ],
                    ),
                  );
                }),
                const Divider(height: 32),
                const Text('Attached Media:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildThumb('Partner', invoiceData['partnerPhoto']),
                    _buildThumb('Receiver', invoiceData['receiverPhoto']),
                    _buildThumb('Items', invoiceData['itemsPhoto']),
                  ],
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.picture_as_pdf),
                    label: const Text('Download PDF Invoice'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    onPressed: () => _downloadPdf(context),
                  ),
                )
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildThumb(String label, String url) {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.network(url, width: 80, height: 80, fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) => Container(width: 80, height: 80, color: Colors.grey, child: const Icon(Icons.image)),
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }
}
