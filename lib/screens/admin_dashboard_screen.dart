import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/api_service.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  List<dynamic> _beneficiaries = [];
  List<dynamic> _filteredBeneficiaries = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String? _selectedDistrict;
  DateTime? _lastSyncTime;

  @override
  void initState() {
    super.initState();
    _fetchBeneficiaries();
  }

  Future<void> _fetchBeneficiaries() async {
    setState(() => _isLoading = true);
    final beneficiaries = await ApiService.getBeneficiaries();
    if (mounted) {
      setState(() {
        _beneficiaries = beneficiaries;
        _lastSyncTime = DateTime.now();
        _applyFilters();
        _isLoading = false;
      });
    }
  }

  void _applyFilters() {
    setState(() {
      _filteredBeneficiaries = _beneficiaries.where((b) {
        final farmerName = (b['farmer_name'] ?? '').toString().toLowerCase();
        final tagNo = (b['tag_no'] ?? '').toString().toLowerCase();
        final fatherName = (b['father_husband_name'] ?? '').toString().toLowerCase();
        final village = (b['village'] ?? '').toString().toLowerCase();
        final district = (b['district'] ?? '').toString().toLowerCase();

        final query = _searchQuery.trim().toLowerCase();
        final matchesSearch = query.isEmpty ||
            farmerName.contains(query) ||
            tagNo.contains(query) ||
            fatherName.contains(query) ||
            village.contains(query);

        final matchesDistrict = _selectedDistrict == null ||
            _selectedDistrict == 'All Districts' ||
            district == _selectedDistrict!.toLowerCase();

        return matchesSearch && matchesDistrict;
      }).toList();
    });
  }

  List<String> get _districts {
    final dists = _beneficiaries
        .map((b) => (b['district'] ?? '').toString().trim())
        .where((d) => d.isNotEmpty)
        .toSet()
        .toList();
    dists.sort();
    return ['All Districts', ...dists];
  }

  int get _totalCattleFeed {
    return _filteredBeneficiaries.fold(0, (sum, b) => sum + ((b['cattle_feed_kg'] ?? 0) as int));
  }

  int get _totalSilage {
    return _filteredBeneficiaries.fold(0, (sum, b) => sum + ((b['silage_kg'] ?? 0) as int));
  }

  Future<void> _downloadUrl(String urlString) async {
    final uri = Uri.parse(urlString);
    try {
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Could not launch URL: $urlString')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error downloading: $e')),
        );
      }
    }
  }

  void _openQrGeneratorModal(Map<String, dynamic> beneficiary) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (modalContext) {
        return _QrGeneratorSuiteModal(
          beneficiary: beneficiary,
          onDownloadPdf: () => _downloadUrl(ApiService.getSingleQrDownloadUrl(beneficiary['tag_no'].toString())),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final primaryBg = const Color(0xFF0F172A);
    final cardBg = const Color(0xFF1E293B);
    final accentCyan = const Color(0xFF06B6D4);
    final accentEmerald = const Color(0xFF10B981);

    return Scaffold(
      backgroundColor: primaryBg,
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 2,
        leading: Builder(
          builder: (context) => IconButton(
            icon: const Icon(Icons.menu_rounded, color: Colors.white),
            onPressed: () => Scaffold.of(context).openDrawer(),
          ),
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: accentCyan.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: accentCyan.withValues(alpha: 0.4)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.cloud_done_rounded, size: 16, color: Color(0xFF38BDF8)),
                  const SizedBox(width: 6),
                  Text(
                    _lastSyncTime != null
                        ? 'SYNCED ${_lastSyncTime!.hour.toString().padLeft(2, '0')}:${_lastSyncTime!.minute.toString().padLeft(2, '0')}'
                        : '360 PARENTING SYNC',
                    style: const TextStyle(
                      color: Color(0xFF38BDF8),
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.1,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Admin Dashboard',
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            tooltip: 'Live Sync from Website',
            onPressed: _fetchBeneficiaries,
          ),
          IconButton(
            icon: const Icon(Icons.qr_code_2_rounded, color: Color(0xFF38BDF8)),
            tooltip: 'Download All Active QRs (Batch PDF)',
            onPressed: () => _downloadUrl(ApiService.getAllQrsDownloadUrl()),
          ),
          const SizedBox(width: 8),
        ],
      ),
      drawer: _buildAdminDrawer(),
      body: Column(
        children: [
          _buildStatsOverview(accentCyan, accentEmerald),
          _buildSearchAndFilterSection(cardBg, accentCyan),
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(color: Color(0xFF38BDF8)),
                  )
                : _filteredBeneficiaries.isEmpty
                    ? _buildEmptyState()
                    : RefreshIndicator(
                        onRefresh: _fetchBeneficiaries,
                        color: const Color(0xFF38BDF8),
                        child: ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          itemCount: _filteredBeneficiaries.length,
                          itemBuilder: (context, index) {
                            final b = _filteredBeneficiaries[index];
                            return _buildBeneficiaryCard(b, cardBg, accentCyan, accentEmerald);
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsOverview(Color accentCyan, Color accentEmerald) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Color(0xFF131D31),
        border: Border(bottom: BorderSide(color: Color(0xFF334155), width: 1)),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildMetricTile(
              label: 'Total Beneficiaries',
              value: '${_filteredBeneficiaries.length}',
              icon: Icons.people_alt_rounded,
              color: const Color(0xFF38BDF8),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildMetricTile(
              label: 'Cattle Feed',
              value: '$_totalCattleFeed kg',
              icon: Icons.pets_rounded,
              color: const Color(0xFF34D399),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildMetricTile(
              label: 'Silage Feed',
              value: '$_totalSilage kg',
              icon: Icons.grass_rounded,
              color: const Color(0xFFFBBF24),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricTile({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(color: Colors.white60, fontSize: 11, fontWeight: FontWeight.w500),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.bold),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildSearchAndFilterSection(Color cardBg, Color accentCyan) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: const Color(0xFF162032),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: TextField(
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Search by Name, Tag #, Village...',
                hintStyle: const TextStyle(color: Colors.white38, fontSize: 13),
                prefixIcon: const Icon(Icons.search_rounded, color: Color(0xFF38BDF8), size: 20),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 0),
                filled: true,
                fillColor: const Color(0xFF0F172A),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF334155)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF38BDF8)),
                ),
              ),
              onChanged: (val) {
                _searchQuery = val;
                _applyFilters();
              },
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            flex: 2,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  isExpanded: true,
                  dropdownColor: const Color(0xFF1E293B),
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  value: _selectedDistrict ?? 'All Districts',
                  icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF38BDF8)),
                  items: _districts
                      .map((d) => DropdownMenuItem(
                            value: d,
                            child: Text(d, overflow: TextOverflow.ellipsis),
                          ))
                      .toList(),
                  onChanged: (val) {
                    setState(() {
                      _selectedDistrict = val;
                      _applyFilters();
                    });
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBeneficiaryCard(
    Map<String, dynamic> b,
    Color cardBg,
    Color accentCyan,
    Color accentEmerald,
  ) {
    final tagNo = (b['tag_no'] ?? '').toString();
    final farmerName = (b['farmer_name'] ?? 'Unknown').toString();
    final fatherName = (b['father_husband_name'] ?? '').toString();
    final village = (b['village'] ?? '').toString();
    final district = (b['district'] ?? '').toString();
    final cattleFeed = b['cattle_feed_kg'] ?? 0;
    final silage = b['silage_kg'] ?? 0;
    final mineral = b['mineral_mixture_kg'] ?? 0;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 6,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(14.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left: Farmer Avatar & Details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          'TAG: #$tagNo',
                          style: const TextStyle(
                            color: Color(0xFF38BDF8),
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      if (district.isNotEmpty)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            district,
                            style: const TextStyle(color: Colors.white70, fontSize: 11),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    farmerName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (fatherName.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      'S/O or W/O: $fatherName',
                      style: const TextStyle(color: Colors.white60, fontSize: 12),
                    ),
                  ],
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.location_on_outlined, size: 14, color: Colors.white60),
                      const SizedBox(width: 4),
                      Text(
                        'Village: $village',
                        style: const TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  // Quota Badges
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      if (cattleFeed > 0)
                        _buildQuotaChip('Feed: ${cattleFeed}kg', const Color(0xFF34D399)),
                      if (silage > 0)
                        _buildQuotaChip('Silage: ${silage}kg', const Color(0xFFFBBF24)),
                      if (mineral > 0)
                        _buildQuotaChip('Mineral: ${mineral}kg', const Color(0xFFA78BFA)),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(width: 12),

            // Right: Parallel QR Code Generator Hub
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Live QR Mini Preview Badge
                GestureDetector(
                  onTap: () => _openQrGeneratorModal(b),
                  child: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(10),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF38BDF8).withValues(alpha: 0.3),
                          blurRadius: 8,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                    child: QrImageView(
                      data: '$tagNo-M1',
                      version: QrVersions.auto,
                      size: 64.0,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                // QR Generator Button
                ElevatedButton.icon(
                  icon: const Icon(Icons.qr_code_scanner_rounded, size: 16),
                  label: const Text('QR Generator', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0284C7),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    elevation: 3,
                  ),
                  onPressed: () => _openQrGeneratorModal(b),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuotaChip(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off_rounded, size: 64, color: Colors.white.withValues(alpha: 0.3)),
          const SizedBox(height: 12),
          const Text(
            'No Beneficiaries Found',
            style: TextStyle(color: Colors.white70, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text(
            'Check search query or tap Refresh to sync from 360 Parenting.',
            style: TextStyle(color: Colors.white38, fontSize: 13),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Live Sync'),
            onPressed: _fetchBeneficiaries,
          ),
        ],
      ),
    );
  }

  Widget _buildAdminDrawer() {
    return Drawer(
      backgroundColor: const Color(0xFF0F172A),
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF0284C7), Color(0xFF0F172A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                const Icon(Icons.admin_panel_settings_rounded, size: 48, color: Colors.white),
                const SizedBox(height: 10),
                const Text(
                  '360 Parenting Hub',
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Text(
                  'Admin Management Portal',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 12),
                ),
              ],
            ),
          ),
          ListTile(
            leading: const Icon(Icons.people_alt_rounded, color: Color(0xFF38BDF8)),
            title: const Text('Beneficiaries & QR Hub', style: TextStyle(color: Colors.white)),
            onTap: () => context.pop(),
          ),
          ListTile(
            leading: const Icon(Icons.qr_code_2_rounded, color: Color(0xFF34D399)),
            title: const Text('Download All QRs (PDF)', style: TextStyle(color: Colors.white)),
            onTap: () {
              context.pop();
              _downloadUrl(ApiService.getAllQrsDownloadUrl());
            },
          ),
          ListTile(
            leading: const Icon(Icons.switch_account_rounded, color: Colors.amber),
            title: const Text('Switch to Supervisor Mode', style: TextStyle(color: Colors.white)),
            onTap: () {
              context.pop();
              context.go('/home');
            },
          ),
          const Divider(color: Color(0xFF334155), indent: 16, endIndent: 16),
          ListTile(
            leading: const Icon(Icons.logout_rounded, color: Colors.redAccent),
            title: const Text('Logout', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
            onTap: () async {
              final router = GoRouter.of(context);
              await ApiService.logout();
              if (mounted) {
                router.go('/login');
              }
            },
          ),
        ],
      ),
    );
  }
}

class _QrGeneratorSuiteModal extends StatefulWidget {
  final Map<String, dynamic> beneficiary;
  final VoidCallback onDownloadPdf;

  const _QrGeneratorSuiteModal({
    required this.beneficiary,
    required this.onDownloadPdf,
  });

  @override
  State<_QrGeneratorSuiteModal> createState() => _QrGeneratorSuiteModalState();
}

class _QrGeneratorSuiteModalState extends State<_QrGeneratorSuiteModal> {
  int _selectedMonth = 1;

  @override
  Widget build(BuildContext context) {
    final tagNo = (widget.beneficiary['tag_no'] ?? '').toString();
    final farmerName = (widget.beneficiary['farmer_name'] ?? 'Unknown').toString();
    final village = (widget.beneficiary['village'] ?? '').toString();
    final qrPayload = '$tagNo-M$_selectedMonth';

    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(20.0),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag Handle
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.white24,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 16),
          // Title & Beneficiary Info
          Text(
            '12-Month QR Generator Suite',
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(
            '$farmerName (Tag #$tagNo - $village)',
            style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 14, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),

          // Month Selector (Horizontal Tabs)
          SizedBox(
            height: 42,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: 12,
              itemBuilder: (context, idx) {
                final month = idx + 1;
                final isSelected = month == _selectedMonth;
                return GestureDetector(
                  onTap: () => setState(() => _selectedMonth = month),
                  child: Container(
                    margin: const EdgeInsets.only(right: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: isSelected ? const Color(0xFF0284C7) : const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF334155),
                      ),
                    ),
                    child: Center(
                      child: Text(
                        'Month $month',
                        style: TextStyle(
                          color: isSelected ? Colors.white : Colors.white70,
                          fontSize: 13,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 20),

          // Rendered Vector QR Code
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.25),
                  blurRadius: 15,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: QrImageView(
              data: qrPayload,
              version: QrVersions.auto,
              size: 180.0,
            ),
          ),
          const SizedBox(height: 16),

          // Payload Token Badge & Copy
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Token: $qrPayload',
                  style: const TextStyle(
                    color: Colors.white,
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 10),
                IconButton(
                  icon: const Icon(Icons.copy_rounded, size: 18, color: Color(0xFF38BDF8)),
                  tooltip: 'Copy Token',
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: qrPayload));
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Copied "$qrPayload" to clipboard!'),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Action Buttons
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.close),
                  label: const Text('Close'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white70,
                    side: const BorderSide(color: Color(0xFF334155)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () => Navigator.pop(context),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.download_rounded),
                  label: const Text('Download 12M PDF'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0284C7),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () {
                    Navigator.pop(context);
                    widget.onDownloadPdf();
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
        ],
      ),
    );
  }
}
