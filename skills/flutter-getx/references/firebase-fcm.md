# Add-on: push notifications (Firebase Cloud Messaging)

Not part of the default scaffold, so a fresh app runs without Firebase config.
Follow this only when the user asks for push notifications or FCM.

Verified on 2026-10-07: the helpers below compile with `flutter analyze`
clean against firebase_core 4.15.0, firebase_messaging 16.7.0 and
awesome_notifications 0.12.1. Check `packages.md` for current versions.

## Steps

1. **Packages** (latest versions, written into pubspec):

   ```bash
   python3 <skill>/scripts/versions.py --write pubspec.yaml --firebase
   flutter pub get
   ```

2. **Connect the Firebase project.** If `lib/firebase_options.dart` does not
   exist yet, copy the placeholder from
   `assets/addons/firebase/lib/firebase_options.dart` so the app compiles and
   runs with push notifications off. Never overwrite an existing one. Then
   the user runs flutterfire with their Firebase account, which replaces the
   placeholder:

   ```bash
   dart pub global activate flutterfire_cli
   flutterfire configure        # writes lib/firebase_options.dart and platform files
   ```

3. **Copy the helpers** from `assets/addons/firebase/lib/utils/` into the
   project's `lib/utils/`:
   * `awesome_notifications_helper.dart`: channels, permission, display, tap routing
   * `fcm_helper.dart`: Firebase init, token saved via `MySharedPref.setFcmToken`,
     foreground messages shown as local notifications, background handler

4. **Wire startup** in `lib/main.dart` after `MySharedPref.init()`:

   ```dart
   import 'utils/awesome_notifications_helper.dart';
   import 'utils/fcm_helper.dart';

   // Local notifications first so FCM can display through them.
   await AwesomeNotificationsHelper.init();
   await FcmHelper.initFcm();
   ```

5. **Platform setup** the helpers cannot do:
   * iOS: in Xcode enable Push Notifications and Background Modes > Remote
     notifications, and upload an APNs key in the Firebase console.
   * iOS deployment target 15.0 or higher (Firebase iOS SDK 12): set
     `platform :ios, '15.0'` in `ios/Podfile` and `IPHONEOS_DEPLOYMENT_TARGET`
     in the Xcode project.
   * awesome_notifications 0.10+ needs two Podfile hooks, or Xcode fails with
     "Using bridging headers with module interfaces is unsupported":

     ```ruby
     post_install do |installer|
       installer.pods_project.targets.each do |target|
         flutter_additional_ios_build_settings(target)
       end
       awesome_pod_file = File.expand_path(File.join('plugins', 'awesome_notifications', 'ios', 'Scripts', 'AwesomePodFile'), '.symlinks')
       require awesome_pod_file
       update_awesome_pod_build_settings(installer)
     end

     awesome_pod_file = File.expand_path(File.join('plugins', 'awesome_notifications', 'ios', 'Scripts', 'AwesomePodFile'), '.symlinks')
     require awesome_pod_file
     update_awesome_main_target_settings('Runner', File.dirname(File.realpath(__FILE__)), flutter_root)
     ```

   * Android 13+: the POST_NOTIFICATIONS permission is requested at runtime by
     `AwesomeNotificationsHelper.init()`. firebase_messaging needs
     `minSdk` 23 or higher; `flutter.minSdkVersion` satisfies it.
   * Check `android/app/build.gradle(.kts)` `minSdk` meets the plugins'
     requirement (see "Android build notes" below).

6. Verify: `flutter analyze` clean, then run on a device and send a test
   message from the Firebase console to the token printed in the log.

## Tapping a notification

Send a `route` key in the FCM data payload:

```json
{ "notification": {"title": "Order shipped", "body": "Tap to track"},
  "data": {"route": "/orders"} }
```

`NotificationController.onActionReceivedMethod` pushes that route through
`Get.key.currentState`, which works even when the app was launched from the
notification. Route values come from `app_routes.dart` (`_Paths`).

## What changed from the reference repo

| Reference (firebase_messaging 14, awesome_notifications 0.9) | Add-on |
|---|---|
| `Firebase.initializeApp()` without options | `options: DefaultFirebaseOptions.currentPlatform` (flutterfire) |
| background handler as a private static method | top-level `fcmBackgroundHandler` with `@pragma('vm:entry-point')` (required for background isolates) |
| token generated once | also listens to `onTokenRefresh` |
| permission requested on every init | only when not already allowed |
| FCM init commented out in `main.dart` | wired explicitly, guarded by try/catch so missing config logs instead of crashing |

## Android build notes

Verification build on 2026-10-07 (Flutter 3.47.5, add-on packages above, a
placeholder `firebase_options.dart`): `flutter build apk --debug` succeeded
with the default `minSdk = flutter.minSdkVersion`. No Gradle edits were
needed. Gradle printed deprecation warnings from the plugins (Java 8 source
level, built-in Kotlin migration); they are upstream and harmless.

If a future version raises its minimum, the build fails with
`uses-sdk:minSdkVersion X cannot be smaller than version Y`. Set
`minSdk = Y` in `android/app/build.gradle.kts` and update this note.
