import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
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

  // Mock data. This should be fetched from the backend using widget.tagNo
  final Map<String, dynamic> farmerInfo = {
    'farmerName': 'Dashri Potai',
    'spouseName': 'Apurv / Etturam Potai',
    'cattleFeed': 22,
    'silage': 55,
  };

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
      var request = http.MultipartRequest('POST', Uri.parse('http://192.168.1.10:8000/api/deliveries/${widget.tagNo}'));
      request.files.add(await http.MultipartFile.fromPath('partner_photo', partnerPhoto!.path));
      request.files.add(await http.MultipartFile.fromPath('receiver_photo', receiverPhoto!.path));
      request.files.add(await http.MultipartFile.fromPath('items_photo', itemsPhoto!.path));
      request.files.add(await http.MultipartFile.fromPath('video_proof', videoProof!.path));

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        if (mounted) context.go('/completion/${widget.tagNo}');
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to upload: ${response.body}')),
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
                    Text('Farmer: ${farmerInfo['farmerName']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text('Spouse/Father: ${farmerInfo['spouseName']}'),
                    const Divider(height: 32),
                    const Text('Subsidies to Deliver:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ListTile(
                      leading: const Icon(Icons.pets),
                      title: const Text('Cattle Feed'),
                      trailing: Text('${farmerInfo['cattleFeed']} kg', style: const TextStyle(fontWeight: FontWeight.bold)),
                    ),
                    ListTile(
                      leading: const Icon(Icons.grass),
                      title: const Text('Silage'),
                      trailing: Text('${farmerInfo['silage']} kg', style: const TextStyle(fontWeight: FontWeight.bold)),
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
