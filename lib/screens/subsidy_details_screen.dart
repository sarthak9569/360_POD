import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/api_service.dart';
import 'dart:io';

class SubsidyDetailsScreen extends StatefulWidget {
  final String tagNo;
  const SubsidyDetailsScreen({super.key, required this.tagNo});

  @override
  State<SubsidyDetailsScreen> createState() => _SubsidyDetailsScreenState();
}

class _SubsidyDetailsScreenState extends State<SubsidyDetailsScreen> {
  final ImagePicker _picker = ImagePicker();

  XFile? partnerPhoto;
  XFile? receiverPhoto;
  XFile? itemsPhoto;
  XFile? videoProof;
  bool _isLoading = false;
  
  bool _isLoadingData = true;
  bool _isInvalidQR = false;
  String _errorMsg = '';
  Map<String, dynamic>? _beneficiaryData;
  int? _month;

  @override
  void initState() {
    super.initState();
    _fetchDetails();
  }

  Future<void> _fetchDetails() async {
    setState(() {
      _isLoadingData = true;
      _errorMsg = '';
    });
    try {
      final response = await http.get(Uri.parse('${ApiService.baseUrl}/qr/${widget.tagNo}'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        if (data['is_completed'] == true) {
          if (mounted) context.pushReplacement('/completion/${widget.tagNo}?alreadyUsed=true');
          return;
        }
        
        final beneficiaryDistrict = data['beneficiary']['district'];
        if (ApiService.currentDistrict != null && 
            beneficiaryDistrict.toString().trim().toLowerCase() != ApiService.currentDistrict!.trim().toLowerCase()) {
          setState(() {
            _errorMsg = 'This QR belongs to $beneficiaryDistrict, but you are logged in for ${ApiService.currentDistrict}.';
            _isInvalidQR = true;
          });
          return;
        }
        
        setState(() {
          _beneficiaryData = data['beneficiary'];
          _month = data['month'];
        });
      } else {
        String errMsg = 'Failed to load details: ${response.statusCode}';
        try {
          final errorData = jsonDecode(response.body);
          if (errorData['detail'] != null) {
            errMsg = errorData['detail'];
          }
        } catch (_) {}
        
        setState(() {
          _errorMsg = errMsg;
        });
      }
    } catch (e) {
      setState(() {
        _errorMsg = 'Error fetching data: $e';
      });
    } finally {
      if (mounted) setState(() => _isLoadingData = false);
    }
  }

  Future<void> _pickMedia(String type) async {
    XFile? pickedFile;
    if (type == 'video') {
      pickedFile = await _picker.pickVideo(source: ImageSource.camera);
      setState(() {
        videoProof = pickedFile;
      });
    } else {
      pickedFile = await _picker.pickImage(source: ImageSource.camera);
      setState(() {
        if (type == 'partner') partnerPhoto = pickedFile;
        if (type == 'receiver') receiverPhoto = pickedFile;
        if (type == 'items') itemsPhoto = pickedFile;
      });
    }
  }

  Future<void> _completeDelivery() async {
    if (partnerPhoto == null || receiverPhoto == null || itemsPhoto == null || videoProof == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please upload all required photos and video')),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final tagToUse = widget.tagNo; // Use the full QR code string
      final success = await ApiService.completeDelivery(
        tagNo: tagToUse,
        partnerPhoto: partnerPhoto!,
        receiverPhoto: receiverPhoto!,
        itemsPhoto: itemsPhoto!,
        videoProof: videoProof!,
      );

      if (success) {
        if (mounted) context.pushReplacement('/completion/$tagToUse');
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to complete delivery.')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Widget _buildUploadSection(String title, XFile? file, String type) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        InkWell(
          onTap: () => _pickMedia(type),
          child: Container(
            height: 100,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.grey[200],
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.grey),
            ),
            child: file != null
                ? type == 'video'
                    ? const Center(child: Icon(Icons.videocam, size: 40, color: Colors.green))
                    : ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(File(file.path), fit: BoxFit.cover),
                      )
                : const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.camera_alt, color: Colors.grey),
                        Text('Tap to Capture'),
                      ],
                    ),
                  ),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingData) {
      return Scaffold(
        appBar: AppBar(title: const Text('Subsidy Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_errorMsg.isNotEmpty || _beneficiaryData == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Subsidy Details')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  _isInvalidQR ? Icons.cancel : Icons.error_outline, 
                  size: _isInvalidQR ? 120 : 60, 
                  color: Colors.red
                ),
                const SizedBox(height: 16),
                if (_isInvalidQR) ...[
                  const Text('INVALID QR', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.red)),
                  const SizedBox(height: 16),
                ],
                Text(
                  _errorMsg, 
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: _isInvalidQR ? 18 : 16)
                ),
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () => context.pop(),
                  child: const Text("Go Back"),
                )
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Subsidy Details')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.green,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text('Month: $_month', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(height: 16),
                    Text('Farmer: ${_beneficiaryData!['farmer_name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text('Father/Husband: ${_beneficiaryData!['father_husband_name']}'),
                    Text('Village: ${_beneficiaryData!['village']}, District: ${_beneficiaryData!['district']}'),
                    const Divider(height: 32),
                    const Text('Subsidies to Deliver:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ListTile(
                      leading: const Icon(Icons.pets),
                      title: const Text('Cattle Feed'),
                      trailing: Text('${_beneficiaryData!['cattle_feed_kg']} kg', style: const TextStyle(fontWeight: FontWeight.bold)),
                    ),
                    ListTile(
                      leading: const Icon(Icons.grass),
                      title: const Text('Silage'),
                      trailing: Text('${_beneficiaryData!['silage_kg']} kg', style: const TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text('Proofs of Delivery', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            _buildUploadSection('1. Delivery Partner Photo', partnerPhoto, 'partner'),
            _buildUploadSection('2. Receiver Photo', receiverPhoto, 'receiver'),
            _buildUploadSection('3. Items Photo', itemsPhoto, 'items'),
            _buildUploadSection('4. Video Proof', videoProof, 'video'),
            const SizedBox(height: 24),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.green,
                foregroundColor: Colors.white,
              ),
              onPressed: _isLoading ? null : _completeDelivery,
              child: _isLoading 
                ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white))
                : const Text('Complete Delivery', style: TextStyle(fontSize: 18)),
            ),
          ],
        ),
      ),
    );
  }
}
