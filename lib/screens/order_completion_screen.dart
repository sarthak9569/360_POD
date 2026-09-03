import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';
import 'image_viewer_screen.dart';

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
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 8),
        GestureDetector(
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => ImageViewerScreen(imageUrl: url, title: label),
              ),
            );
          },
          child: Container(
            width: 240,
            height: 240,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey.shade300, width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.08),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Stack(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(15),
                  child: Image.network(
                    url,
                    width: 240,
                    height: 240,
                    fit: BoxFit.cover,
                    loadingBuilder: (context, child, loadingProgress) {
                      if (loadingProgress == null) return child;
                      return Container(
                        width: 240,
                        height: 240,
                        color: Colors.grey[200],
                        child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
                      );
                    },
                    errorBuilder: (ctx, err, stack) => Container(
                      width: 240,
                      height: 240,
                      color: Colors.grey[200],
                      child: const Center(child: Icon(Icons.broken_image, size: 48, color: Colors.grey)),
                    ),
                  ),
                ),
                Positioned(
                  right: 8,
                  bottom: 8,
                  child: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.6),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Icon(Icons.zoom_in, color: Colors.white, size: 20),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
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
    final district = ben['district'] ?? '';
    final cattleFeed = ben['cattle_feed_kg'] ?? 0;
    final silage = ben['silage_kg'] ?? 0;
    final mineralMixture = ben['mineral_mixture_kg'] ?? 0;
    
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
          Text('Name: $farmerName', style: const TextStyle(fontSize: 15)),
          Text('Village: $village${district.isNotEmpty ? ', $district' : ''}', style: const TextStyle(fontSize: 15)),
          const SizedBox(height: 24),
          
          // Items Details
          const Text('Item Details', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          if (cattleFeed > 0) Text('Cattle Feed: $cattleFeed kg', style: const TextStyle(fontSize: 15)),
          if (silage > 0) Text('Silage: $silage kg', style: const TextStyle(fontSize: 15)),
          if (mineralMixture > 0) Text('Mineral Mixture: $mineralMixture kg', style: const TextStyle(fontSize: 15)),
          if (cattleFeed <= 0 && silage <= 0 && mineralMixture <= 0)
            const Text('No item quantities recorded', style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 24),
          
          // Photo Proofs
          const Center(
            child: Text('Photo Proofs', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 16),
          _buildImagePreview(partnerPhoto, 'Partner Photo'),
          _buildImagePreview(receiverPhoto, 'Receiver Photo'),
          _buildImagePreview(itemsPhoto, 'Items Photo'),
          
          const SizedBox(height: 24),
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
