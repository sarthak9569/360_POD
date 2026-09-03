import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';
import 'pdf_viewer_screen.dart';
import 'image_viewer_screen.dart';

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

  @override
  void initState() {
    super.initState();
    _fetchInvoiceData();
  }

  Future<void> _fetchInvoiceData() async {
    try {
      final response = await http.get(Uri.parse('${ApiService.baseUrl}/deliveries/${widget.tagNo}'));
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
    final Uri url = Uri.parse(ApiService.getInvoicePdfUrl(widget.tagNo));
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      if (context.mounted) {
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
        ),
      );
    }
    
    if (invoiceData == null) {
      return const Center(child: Text("No data found"));
    }

    final ben = invoiceData?['beneficiary'] as Map<String, dynamic>? ?? {};
    final farmerName = ben['farmer_name'] ?? 'Unknown';
    final fatherHusbandName = ben['father_husband_name'] ?? '';
    final village = ben['village'] ?? 'Unknown';
    final district = ben['district'] ?? '';
    
    final cattleFeed = ben['cattle_feed_kg'] ?? 0;
    final silage = ben['silage_kg'] ?? 0;
    final mineralMixture = ben['mineral_mixture_kg'] ?? 0;

    final List<Map<String, String>> deliveredItems = [];
    if (cattleFeed > 0) {
      deliveredItems.add({'name': 'Cattle Feed', 'qty': '$cattleFeed kg'});
    }
    if (silage > 0) {
      deliveredItems.add({'name': 'Silage', 'qty': '$silage kg'});
    }
    if (mineralMixture > 0) {
      deliveredItems.add({'name': 'Mineral Mixture', 'qty': '$mineralMixture kg'});
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
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
              Text('Status: ${invoiceData?['status'] ?? 'Unknown'}', style: const TextStyle(fontWeight: FontWeight.w500)),
              const SizedBox(height: 4),
              Text('Tag Number: ${widget.tagNo}'),
              const SizedBox(height: 4),
              Text('Delivered By: ${invoiceData?['supervisor_name'] ?? ((invoiceData?['partner_name'] == 'Test Partner' || invoiceData?['partner_name'] == null) ? 'Supervisor' : invoiceData?['partner_name'])}'),
              const SizedBox(height: 16),
              const Text('Receiver Details:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 4),
              Text('Name: $farmerName'),
              if (fatherHusbandName.isNotEmpty) Text('Father/Husband: $fatherHusbandName'),
              Text('Address: $village${district.isNotEmpty ? ', $district' : ''}'),
              const Divider(height: 32),
              const Text('Items Delivered:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              
              if (deliveredItems.isNotEmpty)
                ...deliveredItems.map((item) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(item['name']!, style: const TextStyle(fontSize: 15)),
                      Text(item['qty']!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    ],
                  ),
                ))
              else
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 4.0),
                  child: Text('No item quantities recorded', style: TextStyle(color: Colors.grey)),
                ),
              
              const Divider(height: 32),
              const Text('Attached Media:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              const Text('Tap any photo to view full size', style: TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 12),
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
                  label: const Text('View Invoice (PDF)'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  onPressed: () {
                    final String url = ApiService.getInvoicePdfUrl(widget.tagNo);
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
    if (url == null || url.isEmpty || url == "No photo provided") {
      return Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: Colors.grey[200],
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: const Icon(Icons.image_not_supported, color: Colors.grey),
          ),
          const SizedBox(height: 6),
          Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
        ],
      );
    }
    
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ImageViewerScreen(imageUrl: url, title: '$label Photo'),
          ),
        );
      },
      child: Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.grey.shade300, width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.06),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Stack(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(9),
                  child: Image.network(
                    url,
                    width: 80,
                    height: 80,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Container(
                      width: 80,
                      height: 80,
                      color: Colors.grey[300],
                      child: const Icon(Icons.broken_image, color: Colors.grey),
                    ),
                    loadingBuilder: (context, child, loadingProgress) {
                      if (loadingProgress == null) return child;
                      return Container(
                        width: 80,
                        height: 80,
                        color: Colors.grey[200],
                        child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
                      );
                    },
                  ),
                ),
                Positioned(
                  right: 2,
                  bottom: 2,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.6),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.zoom_in, color: Colors.white, size: 14),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
