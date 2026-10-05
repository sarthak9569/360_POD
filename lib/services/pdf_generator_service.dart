import 'dart:io';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:syncfusion_flutter_pdf/pdf.dart';

class PdfGeneratorService {
  /// Generates a 36-coupon booklet PDF natively on the mobile device.
  static Future<File?> generateCouponBookletPdf(Map<String, dynamic> beneficiary) async {
    try {
      final PdfDocument document = PdfDocument();
      document.pageSettings.margins.all = 20;

      final tagNo = (beneficiary['tag_no'] ?? 'UNKNOWN').toString();
      final farmerName = (beneficiary['farmer_name'] ?? 'Beneficiary Name').toString();
      final fatherHusband = (beneficiary['father_husband_name'] ?? '-').toString();
      final village = (beneficiary['village'] ?? '-').toString();
      final district = (beneficiary['district'] ?? '-').toString();

      final List<Map<String, dynamic>> products = [
        {"name": "Silage Feed", "code": "SILAGE", "qty": beneficiary['silage_kg'] ?? 50},
        {"name": "Cattle Feed", "code": "CATTLEFEED", "qty": beneficiary['cattle_feed_kg'] ?? 25},
        {"name": "Mineral Mixture", "code": "MINERALS", "qty": beneficiary['mineral_mixture_kg'] ?? 5},
      ];

      PdfPage page = document.pages.add();
      PdfGraphics graphics = page.graphics;

      PdfFont fontTitle = PdfStandardFont(PdfFontFamily.helvetica, 14, style: PdfFontStyle.bold);
      PdfFont fontBold = PdfStandardFont(PdfFontFamily.helvetica, 10, style: PdfFontStyle.bold);
      PdfFont fontRegular = PdfStandardFont(PdfFontFamily.helvetica, 9);

      // Header Banner
      graphics.drawRectangle(
        brush: PdfSolidBrush(PdfColor(16, 78, 118)),
        bounds: Rect.fromLTWH(0, 0, page.getClientSize().width, 45),
      );
      graphics.drawString(
        "360 PARENTING - BENEFICIARY SUBSIDY BOOKLET",
        fontTitle,
        brush: PdfBrushes.white,
        bounds: Rect.fromLTWH(10, 12, page.getClientSize().width - 20, 30),
      );

      // Beneficiary Details Box
      double y = 55;
      graphics.drawString("Tag No: $tagNo", fontBold, bounds: Rect.fromLTWH(10, y, 200, 18));
      graphics.drawString("Farmer: $farmerName", fontBold, bounds: Rect.fromLTWH(220, y, 250, 18));
      y += 18;
      graphics.drawString("Father/Husband: $fatherHusband", fontRegular, bounds: Rect.fromLTWH(10, y, 200, 18));
      graphics.drawString("Village: $village, District: $district", fontRegular, bounds: Rect.fromLTWH(220, y, 250, 18));
      y += 28;

      // Table for 36 Coupons
      PdfGrid grid = PdfGrid();
      grid.columns.add(count: 5);
      grid.headers.add(1);

      PdfGridRow header = grid.headers[0];
      header.cells[0].value = "Month";
      header.cells[1].value = "Product Name";
      header.cells[2].value = "Quantity";
      header.cells[3].value = "QR Coupon Code";
      header.cells[4].value = "Validity";

      for (int i = 0; i < 5; i++) {
        header.cells[i].style.backgroundBrush = PdfSolidBrush(PdfColor(16, 78, 118));
        header.cells[i].style.textBrush = PdfBrushes.white;
        header.cells[i].style.font = fontBold;
      }

      for (int m = 1; m <= 12; m++) {
        for (var prod in products) {
          PdfGridRow row = grid.rows.add();
          row.cells[0].value = "Month $m";
          row.cells[1].value = prod['name'];
          row.cells[2].value = "${prod['qty']} kg";
          row.cells[3].value = "$tagNo-M$m-${prod['code']}";
          row.cells[4].value = "VALID FOR MONTH $m";
        }
      }

      grid.draw(page: page, bounds: Rect.fromLTWH(0, y, page.getClientSize().width, 0));

      final List<int> bytes = await document.save();
      document.dispose();

      final Directory dir = await getApplicationDocumentsDirectory();
      final File file = File('${dir.path}/Coupon_Booklet_$tagNo.pdf');
      await file.writeAsBytes(bytes);
      return file;
    } catch (e) {
      debugPrint('Error generating native PDF booklet: $e');
      return null;
    }
  }
}
