import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'pdf_viewer_screen.dart';

class InvoiceScreen extends StatefulWidget {
  final String tagNo;
  const InvoiceScreen({super.key, required this.tagNo});

  @override
  State<InvoiceScreen> createState() => _InvoiceScreenState();
}

class _InvoiceScreenState extends State<InvoiceScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic>? invoiceData;
  
  final String baseUrl = 'http://192.168.1.10:8000';

  @override
  void initState() {
    super.initState();
    _fetchInvoiceData();
  }

  Future<void> _fetchInvoiceData() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/deliveries/${widget.tagNo}'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          invoiceData = data;
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = "Failed to load invoice: ${response.statusCode}";
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = "Network error: $e";
        _isLoading = false;
      });
    }
  }

  Future<void> _downloadPdf(BuildContext context) async {
    final Uri url = Uri.parse('$baseUrl/api/deliveries/${widget.tagNo}/invoice.pdf');
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
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
            onPressed: (_isLoading || _errorMessage != null) ? null : () => _downloadPdf(context),
            tooltip: 'Download PDF',
          )
        ],
      ),
      body: _buildBody(),
    );
  }
  
  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 60),
            const SizedBox(height: 16),
            Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _isLoading = true;
                  _errorMessage = null;
                });
                _fetchInvoiceData();
              },
              child: const Text("Retry"),
            )
          ],
        )
      );
    }
    
    if (invoiceData == null) {
      return const Center(child: Text("No data found"));
    }

    return SingleChildScrollView(
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
              Text('Status: ${invoiceData?['status'] ?? 'Unknown'}'),
              Text('Tag Number: ${widget.tagNo}'),
              Text('Delivered By: ${invoiceData?['partner_name'] ?? 'Unknown'}'),
              const SizedBox(height: 16),
              const Text('Receiver Details:', style: TextStyle(fontWeight: FontWeight.bold)),
              const Text('Name: Dashri Potai'), // Hardcoded based on existing UI
              const Text('Address: Ghodagaon, Kanker'),
              const Divider(height: 32),
              const Text('Items Delivered:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              
              // Hardcoded items based on existing UI, ideally these should be in the DB too
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text('Cattle Feed'),
                    Text('22 kg', style: TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text('Silage'),
                    Text('55 kg', style: TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              
              const Divider(height: 32),
              const Text('Attached Media:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildThumb('Partner', invoiceData?['partner_photo_url']),
                  _buildThumb('Receiver', invoiceData?['receiver_photo_url']),
                  _buildThumb('Items', invoiceData?['items_photo_url']),
                ],
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.visibility),
                  label: const Text('View Invoice'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  onPressed: () {
                    final String url = '$baseUrl/api/deliveries/${widget.tagNo}/invoice.pdf';
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => PdfViewerScreen(pdfUrl: url),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.download),
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
    );
  }

  Widget _buildThumb(String label, String? url) {
    if (url == null || url.isEmpty) {
      return Column(
        children: [
          Container(width: 80, height: 80, color: Colors.grey[300], child: const Icon(Icons.image_not_supported, color: Colors.grey)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      );
    }
    
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.network(url, width: 80, height: 80, fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) => Container(width: 80, height: 80, color: Colors.grey[300], child: const Icon(Icons.broken_image, color: Colors.grey)),
            loadingBuilder: (context, child, loadingProgress) {
              if (loadingProgress == null) return child;
              return Container(
                width: 80, height: 80, color: Colors.grey[200],
                child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
              );
            },
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }
}
