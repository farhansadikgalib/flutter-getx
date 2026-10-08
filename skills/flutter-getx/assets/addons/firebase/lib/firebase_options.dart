// Placeholder written by the flutter-getx skill so the app compiles before
// Firebase is connected. `flutterfire configure` replaces this file with the
// real options for your Firebase project.
//
// Until then FcmHelper.initFcm() catches the error below, logs it, and the app
// runs without push notifications.
import 'package:firebase_core/firebase_core.dart';

class DefaultFirebaseOptions {
  DefaultFirebaseOptions._();

  static FirebaseOptions get currentPlatform => throw UnsupportedError(
        'Firebase is not configured yet. Run `flutterfire configure` in the '
        'project root to generate lib/firebase_options.dart.',
      );
}
