import 'package:awesome_notifications/awesome_notifications.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../app/routes/app_pages.dart';

/// Local notifications (channels, permission, display, tap handling).
/// FCM payloads are shown through [showNotification].
class AwesomeNotificationsHelper {
  AwesomeNotificationsHelper._();

  static final AwesomeNotifications _notifications = AwesomeNotifications();

  static Future<void> init() async {
    await _notifications.initialize(
      null, // null = app icon
      [
        NotificationChannel(
          channelGroupKey: NotificationChannels.generalChannelGroupKey,
          channelKey: NotificationChannels.generalChannelKey,
          channelName: NotificationChannels.generalChannelName,
          channelDescription: NotificationChannels.generalChannelDescription,
          defaultColor: Colors.green,
          ledColor: Colors.white,
          channelShowBadge: true,
          playSound: true,
          importance: NotificationImportance.Max,
        ),
        NotificationChannel(
          channelGroupKey: NotificationChannels.chatChannelGroupKey,
          channelKey: NotificationChannels.chatChannelKey,
          channelName: NotificationChannels.chatChannelName,
          channelDescription: NotificationChannels.chatChannelDescription,
          defaultColor: Colors.green,
          ledColor: Colors.white,
          channelShowBadge: true,
          playSound: true,
          importance: NotificationImportance.Max,
        ),
      ],
      channelGroups: [
        NotificationChannelGroup(
          channelGroupKey: NotificationChannels.generalChannelGroupKey,
          channelGroupName: NotificationChannels.generalChannelGroupName,
        ),
        NotificationChannelGroup(
          channelGroupKey: NotificationChannels.chatChannelGroupKey,
          channelGroupName: NotificationChannels.chatChannelGroupName,
        ),
      ],
    );

    await _notifications.setListeners(
      onActionReceivedMethod: NotificationController.onActionReceivedMethod,
    );

    if (!await _notifications.isNotificationAllowed()) {
      await _notifications.requestPermissionToSendNotifications();
    }
  }

  static Future<void> showNotification({
    required int id,
    required String title,
    required String body,
    String? channelKey,
    Map<String, String?>? payload,
    NotificationLayout layout = NotificationLayout.Default,
    String? largeIcon,
    List<NotificationActionButton>? actionButtons,
  }) async {
    if (!await _notifications.isNotificationAllowed()) return;
    await _notifications.createNotification(
      content: NotificationContent(
        id: id,
        channelKey: channelKey ?? NotificationChannels.generalChannelKey,
        title: title,
        body: body,
        payload: payload,
        notificationLayout: layout,
        largeIcon: largeIcon,
        autoDismissible: true,
        showWhen: true,
      ),
      actionButtons: actionButtons,
    );
  }
}

class NotificationController {
  /// Runs when the user taps a notification. Must be static and top-level
  /// reachable for background isolates.
  @pragma('vm:entry-point')
  static Future<void> onActionReceivedMethod(ReceivedAction action) async {
    final route = action.payload?['route'];
    // Use the navigator key: Get.toNamed may run before the app is ready.
    Get.key.currentState?.pushNamed(route ?? Routes.HOME);
  }
}

class NotificationChannels {
  NotificationChannels._();

  static const generalChannelKey = 'general_channel';
  static const generalChannelName = 'General notifications';
  static const generalChannelDescription = 'Notification channel for general notifications';
  static const generalChannelGroupKey = 'general_channel_group';
  static const generalChannelGroupName = 'General';

  static const chatChannelKey = 'chat_channel';
  static const chatChannelName = 'Chat notifications';
  static const chatChannelDescription = 'Notification channel for chat messages';
  static const chatChannelGroupKey = 'chat_channel_group';
  static const chatChannelGroupName = 'Chat';
}
