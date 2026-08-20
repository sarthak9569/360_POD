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

  static Future<List<String>> getDistricts() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/districts'));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.cast<String>();
      }
    } catch (e) {
      debugPrint('Error fetching districts: $e');
    }
    return [];
  }

  static Future<List<String>> getVillages(String district) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/districts/$district/villages'));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.cast<String>();
      }
    } catch (e) {
      debugPrint('Error fetching villages: $e');
    }
    return [];
  }

  static Future<bool> partnerLogin({
    required String district,
    required String village,
    required String supervisorName,
    required String partnerName,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/partner/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'district': district,
          'village': village,
          'supervisor_name': supervisorName,
          'partner_name': partnerName,
        }),
      );
      if (response.statusCode == 200) {
        return true;
      } else {
        final data = jsonDecode(response.body);
        debugPrint('Login failed: ${data["detail"]}');
        return false;
      }
    } catch (e) {
      debugPrint('Error logging in partner: $e');
      return false;
    }
  }

  static Future<List<dynamic>> getSupervisors() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/supervisors'));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint('Error fetching supervisors: $e');
    }
    return [];
  }

  static Future<bool> createSupervisor({
    required String name,
    required List<String> districts,
    required List<String> villages,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/supervisors'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'districts': districts,
          'villages': villages,
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error creating supervisor: $e');
      return false;
    }
  }

  static Future<bool> updateSupervisor({
    required String id,
    required String name,
    required List<String> districts,
    required List<String> villages,
  }) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/supervisors/$id'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'districts': districts,
          'villages': villages,
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error updating supervisor: $e');
      return false;
    }
  }

  static Future<bool> deleteSupervisor(String id) async {
    try {
      final response = await http.delete(Uri.parse('$baseUrl/supervisors/$id'));
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error deleting supervisor: $e');
      return false;
    }
  }
}
