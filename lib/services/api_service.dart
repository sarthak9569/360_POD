import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:flutter/foundation.dart';

class ApiService {
  // Base URL provided by Railway
  static const String baseUrl = 'https://proof-of-delivery-2-production.up.railway.app/api';

  /// Fetch a delivery record by tag number
  static Future<Map<String, dynamic>?> getDelivery(String tagNo) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/deliveries/$tagNo'));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      debugPrint('Error fetching delivery: $e');
      return null;
    }
  }

  /// Upload delivery proofs to the backend
  static Future<bool> completeDelivery({
    required String tagNo,
    required XFile partnerPhoto,
    required XFile receiverPhoto,
    required XFile itemsPhoto,
    required XFile videoProof,
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/deliveries/$tagNo'));
      
      request.files.add(await http.MultipartFile.fromPath('partner_photo', partnerPhoto.path));
      request.files.add(await http.MultipartFile.fromPath('receiver_photo', receiverPhoto.path));
      request.files.add(await http.MultipartFile.fromPath('items_photo', itemsPhoto.path));
      request.files.add(await http.MultipartFile.fromPath('video_proof', videoProof.path));

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        debugPrint('Delivery completed successfully');
        return true;
      } else {
        debugPrint('Failed to complete delivery: ${response.statusCode} - ${response.body}');
        return false;
      }
    } catch (e) {
      debugPrint('Error completing delivery: $e');
      return false;
    }
  }

  /// Get the URL for downloading/viewing the invoice PDF
  static String getInvoicePdfUrl(String tagNo) {
    return '$baseUrl/deliveries/$tagNo/invoice.pdf';
  }
}
