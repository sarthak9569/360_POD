import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // Configurable base URL for FastAPI / 360 Parenting gateway
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000/api';
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:8000/api';
    return 'http://localhost:8000/api';
  }

  // Store the partner's logged in district and supervisor globally
  static String? currentDistrict;
  static String? currentSupervisorName;
  static String? currentPartnerName;

  /// SharedPreferences Keys
  static const String _keyIsLoggedIn = 'is_logged_in';
  static const String _keyUserRole = 'user_role'; // 'partner' or 'admin'
  static const String _keyDistrict = 'saved_district';
  static const String _keyVillage = 'saved_village';
  static const String _keySupervisorName = 'saved_supervisor_name';
  static const String _keyPartnerName = 'saved_partner_name';

  /// Save partner login session to SharedPreferences
  static Future<void> savePartnerSession({
    required String district,
    required String village,
    required String supervisorName,
    required String partnerName,
  }) async {
    currentDistrict = district;
    currentSupervisorName = supervisorName;
    currentPartnerName = partnerName;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_keyIsLoggedIn, true);
      await prefs.setString(_keyUserRole, 'partner');
      await prefs.setString(_keyDistrict, district);
      await prefs.setString(_keyVillage, village);
      await prefs.setString(_keySupervisorName, supervisorName);
      await prefs.setString(_keyPartnerName, partnerName);
    } catch (e) {
      debugPrint('Error saving partner session to SharedPreferences: $e');
    }
  }

  /// Save admin login session to SharedPreferences
  static Future<void> saveAdminSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_keyIsLoggedIn, true);
      await prefs.setString(_keyUserRole, 'admin');
    } catch (e) {
      debugPrint('Error saving admin session to SharedPreferences: $e');
    }
  }

  /// Get saved session data from SharedPreferences
  static Future<Map<String, dynamic>?> getSavedSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final isLoggedIn = prefs.getBool(_keyIsLoggedIn) ?? false;
      if (!isLoggedIn) return null;

      final role = prefs.getString(_keyUserRole) ?? 'partner';
      final district = prefs.getString(_keyDistrict);
      final supervisorName = prefs.getString(_keySupervisorName);
      final partnerName = prefs.getString(_keyPartnerName);
      
      if (district != null) {
        currentDistrict = district;
      }
      if (supervisorName != null) {
        currentSupervisorName = supervisorName;
      }
      if (partnerName != null) {
        currentPartnerName = partnerName;
      }

      return {
        'isLoggedIn': true,
        'role': role,
        'district': district,
        'village': prefs.getString(_keyVillage),
        'supervisorName': supervisorName,
        'partnerName': partnerName,
      };
    } catch (e) {
      debugPrint('Error reading session from SharedPreferences: $e');
      return null;
    }
  }

  /// Clear session on logout
  static Future<void> logout() async {
    currentDistrict = null;
    currentSupervisorName = null;
    currentPartnerName = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.clear();
    } catch (e) {
      debugPrint('Error clearing SharedPreferences on logout: $e');
    }
  }

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
      
      if (currentDistrict != null) {
        request.fields['supervisor_district'] = currentDistrict!;
      }
      if (currentSupervisorName != null && currentSupervisorName!.isNotEmpty) {
        request.fields['supervisor_name'] = currentSupervisorName!;
        request.fields['partner_name'] = currentPartnerName!;
      } else if (currentPartnerName != null && currentPartnerName!.isNotEmpty) {
        request.fields['partner_name'] = currentPartnerName!;
      }
      
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

  static Future<List<dynamic>> getBeneficiaries() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/beneficiaries'));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint('Error fetching beneficiaries: $e');
    }
    return [];
  }

  static String getSingleQrDownloadUrl(String tagNo) {
    return '$baseUrl/beneficiaries/$tagNo/qrs/download';
  }

  static String getAllQrsDownloadUrl() {
    return '$baseUrl/beneficiaries/qrs/download';
  }
}
