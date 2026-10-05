import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_pdfviewer/pdfviewer.dart';

class PdfViewerScreen extends StatelessWidget {
  final String? title;
  final String? pdfUrl;
  final File? pdfFile;
  final Uint8List? pdfBytes;

  const PdfViewerScreen({
    super.key,
    this.title,
    this.pdfUrl,
    this.pdfFile,
    this.pdfBytes,
  });

  @override
  Widget build(BuildContext context) {
    Widget viewerWidget;
    if (pdfFile != null) {
      viewerWidget = SfPdfViewer.file(pdfFile!);
    } else if (pdfBytes != null) {
      viewerWidget = SfPdfViewer.memory(pdfBytes!);
    } else if (pdfUrl != null && pdfUrl!.isNotEmpty) {
      viewerWidget = SfPdfViewer.network(pdfUrl!);
    } else {
      viewerWidget = const Center(
        child: Text('No PDF document available.', style: TextStyle(color: Colors.white70)),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: Text(title ?? 'Coupon Booklet PDF', style: const TextStyle(color: Colors.white, fontSize: 16)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: viewerWidget,
    );
  }
}
