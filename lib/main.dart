import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/subsidy_details_screen.dart';
import 'screens/order_completion_screen.dart';
import 'screens/invoice_screen.dart';
import 'screens/admin_dashboard_screen.dart';

void main() {
  runApp(const ProofOfDeliveryApp());
}

final GoRouter _router = GoRouter(
  initialLocation: '/login',
  routes: <RouteBase>[
    GoRoute(
      path: '/login',
      builder: (BuildContext context, GoRouterState state) {
        return const LoginScreen();
      },
    ),
    GoRoute(
      path: '/home',
      builder: (BuildContext context, GoRouterState state) {
        return const HomeScreen();
      },
    ),
    GoRoute(
      path: '/admin',
      builder: (BuildContext context, GoRouterState state) {
        return const AdminDashboardScreen();
      },
    ),
    GoRoute(
      path: '/subsidy/:tagNo',
      builder: (BuildContext context, GoRouterState state) {
        final tagNo = state.pathParameters['tagNo']!;
        return SubsidyDetailsScreen(tagNo: tagNo);
      },
    ),
    GoRoute(
      path: '/completion/:tagNo',
      builder: (BuildContext context, GoRouterState state) {
        final tagNo = state.pathParameters['tagNo']!;
        final alreadyUsed = state.uri.queryParameters['alreadyUsed'] == 'true';
        return OrderCompletionScreen(tagNo: tagNo, alreadyUsed: alreadyUsed);
      },
    ),
    GoRoute(
      path: '/invoice/:tagNo',
      builder: (BuildContext context, GoRouterState state) {
        final tagNo = state.pathParameters['tagNo']!;
        return InvoiceScreen(tagNo: tagNo);
      },
    ),
  ],
);

class ProofOfDeliveryApp extends StatelessWidget {
  const ProofOfDeliveryApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'Proof of Delivery',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      routerConfig: _router,
    );
  }
}
