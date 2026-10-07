import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:logger/logger.dart';

import '../app/data/local/my_shared_pref.dart';
import '../firebase_options.dart';
import 'awesome_notifications_helper.dart';

/// Must be a top-level function: FCM runs it in a background isolate.
@pragma('vm:entry-point')
Future<void> fcmBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  // Notification messages are displayed by the OS in the background; handle
  // data-only messages here if you send them.
}

/// Firebase Cloud Messaging setup: permission, token, and foreground display.
class FcmHelper {
  FcmHelper._();

  static Future<void> initFcm() async {
    try {
      await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
      final messaging = FirebaseMessaging.instance;

      await messaging.requestPermission(alert: true, badge: true, sound: true);
      // iOS: let our local notification show instead of the system one.
      await messaging.setForegroundNotificationPresentationOptions(
        alert: false,
        badge: true,
        sound: false,
      );

      await _saveToken(await messaging.getToken());
      messaging.onTokenRefresh.listen(_saveToken);

      FirebaseMessaging.onBackgroundMessage(fcmBackgroundHandler);
      FirebaseMessaging.onMessage.listen(_onForegroundMessage);
    } catch (error, stackTrace) {
      // Missing google-services.json / GoogleService-Info.plist lands here.
      Logger().e('FCM init failed', error: error, stackTrace: stackTrace);
    }
  }

  static Future<void> _saveToken(String? token) async {
    if (token == null) return;
    Logger().i('FCM token: $token');
    await MySharedPref.setFcmToken(token);
    // TODO: send the token to your backend.
  }

  static Future<void> _onForegroundMessage(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;
    await AwesomeNotificationsHelper.showNotification(
      id: message.hashCode,
      title: notification.title ?? '',
      body: notification.body ?? '',
      payload: message.data.map((k, v) => MapEntry(k, v.toString())),
    );
  }
}
