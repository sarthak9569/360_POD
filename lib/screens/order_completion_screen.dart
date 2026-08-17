import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';

class OrderCompletionScreen extends StatefulWidget {
  final String tagNo;
  final bool alreadyUsed;
  const OrderCompletionScreen({super.key, required this.tagNo, this.alreadyUsed = false});

  @override
  State<OrderCompletionScreen> createState() => _OrderCompletionScreenState();
}

class _OrderCompletionScreenState extends State<OrderCompletionScreen> {
  Map<String, dynamic>? _deliveryData;
  bool _isLoading = true;
  String _errorMsg = '';

  @override
  void initState() {
    super.initState();
    _fetchDeliveryDetails();
  }

  Future<void> _fetchDeliveryDetails() async {
    setState(() {
      _isLoading = true;
      _errorMsg = '';
    });
    try {
      final response = await http.get(Uri.parse('${ApiService.baseUrl}/deliveries/${widget.tagNo}'));
      if (response.statusCode == 200) {
        setState(() {
          _deliveryData = jsonDecode(response.body);
        });
      } else {
        setState(() {
          _errorMsg = 'Failed to load delivery details (Status ${response.statusCode})';
        });
      }
    } catch (e) {
      setState(() {
        _errorMsg = 'Error loading delivery data: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Widget _buildImagePreview(String url, String label) {
    if (url.isEmpty || url == "No photo provided") return const SizedBox.shrink();
    return Column(
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.network(
            url,
            height: 120,
            width: double.infinity,
            fit: BoxFit.cover,
            errorBuilder: (ctx, err, stack) => Container(
              height: 120,
              color: Colors.grey[200],
              child: const Center(child: Icon(Icons.broken_image)),
            ),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.alreadyUsed ? 'Subsidy Redeemed' : 'Delivery Complete'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: _isLoading 
          ? const Center(child: CircularProgressIndicator())
          : _errorMsg.isNotEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_errorMsg, style: const TextStyle(color: Colors.red)),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _fetchDeliveryDetails, child: const Text('Retry')),
                      OutlinedButton(onPressed: () => context.go('/home'), child: const Text('Back to Home')),
                    ],
                  ),
                )
              : _buildContent(context),
    );
  }

  Widget _buildContent(BuildContext context) {
    final ben = _deliveryData?['beneficiary'] ?? {};
    final farmerName = ben['farmer_name'] ?? 'Unknown';
    final village = ben['village'] ?? 'Unknown';
    final cattleFeed = ben['cattle_feed_kg'] ?? 0;
    final silage = ben['silage_kg'] ?? 0;
    
    final partnerPhoto = _deliveryData?['partner_photo_url'] ?? '';
    final receiverPhoto = _deliveryData?['receiver_photo_url'] ?? '';
    final itemsPhoto = _deliveryData?['items_photo_url'] ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(
            widget.alreadyUsed ? Icons.info : Icons.check_circle, 
            size: 80, 
            color: widget.alreadyUsed ? Colors.orange : Colors.green
          ),
          const SizedBox(height: 16),
          Text(
            widget.alreadyUsed ? 'Subsidy Redeemed Already' : 'Delivery Complete',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'QR Code ID: ${widget.tagNo}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16, color: Colors.grey),
          ),
          const Divider(height: 48),
          
          // Farmer Details
          const Text('Farmer Details', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('Name: $farmerName'),
          Text('Village: $village'),
          const SizedBox(height: 24),
          
          // Items Details
          const Text('Item Details', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('Cattle Feed: $cattleFeed kg'),
          Text('Silage: $silage kg'),
          const SizedBox(height: 24),
          
          // Photo Proofs
          const Text('Photo Proofs', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          _buildImagePreview(partnerPhoto, 'Partner Photo'),
          _buildImagePreview(receiverPhoto, 'Receiver Photo'),
          _buildImagePreview(itemsPhoto, 'Items Photo'),
          
          const SizedBox(height: 32),
          ElevatedButton.icon(
            icon: const Icon(Icons.receipt_long),
            label: const Text('View / Download Invoice'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            onPressed: () {
              context.push('/invoice/${widget.tagNo}');
            },
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            icon: const Icon(Icons.home),
            label: const Text('Back to Home'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            onPressed: () {
              context.go('/home');
            },
          )
        ],
      ),
    );
  }
}
