import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class AddBeneficiaryScreen extends StatefulWidget {
  const AddBeneficiaryScreen({super.key});

  @override
  State<AddBeneficiaryScreen> createState() => _AddBeneficiaryScreenState();
}

class _SubsidyEntry {
  String? product;
  final TextEditingController quantityController = TextEditingController();
}

class _AddBeneficiaryScreenState extends State<AddBeneficiaryScreen> {
  final _formKey = GlobalKey<FormState>();
  
  final _tagNoController = TextEditingController();
  final _farmerNameController = TextEditingController();
  final _fatherNameController = TextEditingController();
  final _villageController = TextEditingController();
  final _districtController = TextEditingController();

  final List<String> _availableProducts = ['Cattle Feed', 'Silage', 'Mineral Mixture'];
  final List<_SubsidyEntry> _subsidies = [];

  bool _isSubmitting = false;

  void _addSubsidy() {
    setState(() {
      _subsidies.add(_SubsidyEntry());
    });
  }

  void _removeSubsidy(int index) {
    setState(() {
      _subsidies[index].quantityController.dispose();
      _subsidies.removeAt(index);
    });
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;
    
    // Check if duplicate products are selected
    final selectedProducts = _subsidies.map((s) => s.product).where((p) => p != null).toList();
    if (selectedProducts.length != selectedProducts.toSet().length) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Cannot select the same subsidy product multiple times')));
      return;
    }

    setState(() => _isSubmitting = true);
    
    int cattleFeed = 0;
    int silage = 0;
    int mineral = 0;

    for (var s in _subsidies) {
      final qty = int.tryParse(s.quantityController.text) ?? 0;
      if (s.product == 'Cattle Feed') cattleFeed += qty;
      else if (s.product == 'Silage') silage += qty;
      else if (s.product == 'Mineral Mixture') mineral += qty;
    }
    
    try {
      final requestBody = {
        "tag_no": _tagNoController.text.trim(),
        "farmer_name": _farmerNameController.text.trim(),
        "father_husband_name": _fatherNameController.text.trim(),
        "village": _villageController.text.trim(),
        "district": _districtController.text.trim(),
        "cattle_feed_kg": cattleFeed,
        "silage_kg": silage,
        "mineral_mixture_kg": mineral,
      };

      final response = await http.post(
        Uri.parse('http://localhost:8000/api/beneficiaries'), // Assuming the user is running backend locally or via Railway
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        // Response should be the PDF file
        final directory = await getApplicationDocumentsDirectory();
        final file = File('${directory.path}/QRs_${_tagNoController.text}.pdf');
        await file.writeAsBytes(response.bodyBytes);
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Beneficiary added! PDF saved to ${file.path}')),
          );
          Navigator.pop(context); // Go back to dashboard
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error: ${response.body}')),
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
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  void dispose() {
    _tagNoController.dispose();
    _farmerNameController.dispose();
    _fatherNameController.dispose();
    _villageController.dispose();
    _districtController.dispose();
    for (var s in _subsidies) {
      s.quantityController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add Beneficiary'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _tagNoController,
                decoration: const InputDecoration(labelText: 'Tag Number *', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _farmerNameController,
                decoration: const InputDecoration(labelText: 'Beneficiary Name *', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _fatherNameController,
                decoration: const InputDecoration(labelText: 'Father/Husband Name *', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _villageController,
                decoration: const InputDecoration(labelText: 'Village *', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _districtController,
                decoration: const InputDecoration(labelText: 'District *', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 32),
              const Text('Subsidies (Optional)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              ..._subsidies.asMap().entries.map((entry) {
                int index = entry.key;
                _SubsidyEntry subsidy = entry.value;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 16.0),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: DropdownButtonFormField<String>(
                          value: subsidy.product,
                          decoration: const InputDecoration(border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 12)),
                          hint: const Text('Select Product'),
                          items: _availableProducts.map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
                          onChanged: (val) => setState(() => subsidy.product = val),
                          validator: (v) => v == null ? 'Required' : null,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        flex: 1,
                        child: TextFormField(
                          controller: subsidy.quantityController,
                          decoration: const InputDecoration(labelText: 'Qty (kg)', border: OutlineInputBorder()),
                          keyboardType: TextInputType.number,
                          validator: (v) => (v == null || v.isEmpty || int.tryParse(v) == null) ? 'Invalid' : null,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.remove_circle, color: Colors.red),
                        onPressed: () => _removeSubsidy(index),
                      )
                    ],
                  ),
                );
              }),
              TextButton.icon(
                onPressed: _subsidies.length < _availableProducts.length ? _addSubsidy : null,
                icon: const Icon(Icons.add),
                label: const Text('Add Subsidy Product'),
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                onPressed: _isSubmitting ? null : _submitForm,
                child: _isSubmitting
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text('Save and Generate QR PDF', style: TextStyle(fontSize: 18)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
