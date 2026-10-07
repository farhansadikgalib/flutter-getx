# Testing

Tests live in `test/`, mirroring `lib/` names (`users_controller_test.dart`).
The scaffold ships four passing tests: `widget_test.dart`,
`api_client_test.dart`, `my_hive_test.dart`, `locale_switch_test.dart`. Run everything with
`flutter test`.

## Setup cheatsheet

| Need | Do |
|---|---|
| GetX without navigation side effects | `Get.testMode = true;` in `setUp` |
| Clean DI between tests | `tearDown(Get.reset);` |
| A controller that `BaseController`/`BaseView` expects | `Get.put(ConnectionManagerController());` |
| No real HTTP | `DioAdapter(dio: BaseClient.dio)` from `http_mock_adapter` |
| SharedPreferences | `SharedPreferences.setMockInitialValues({}); MySharedPref.setStorage(await SharedPreferences.getInstance());` |
| Hive | `MyHive.init(testPath: tempDir.path, registerAdapters: ...)` |
| google_fonts | `GoogleFonts.config.allowRuntimeFetching = false;` |
| Platform channels in plain `test()` | `TestWidgetsFlutterBinding.ensureInitialized();` |

## Controller test with a mocked API

Verifies the status transitions for the networking example.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http_mock_adapter/http_mock_adapter.dart';

import 'package:my_shop/app/core/connection_manager/connection_manager_controller.dart';
import 'package:my_shop/app/modules/users/controllers/users_controller.dart';
import 'package:my_shop/app/services/api_call_status.dart';
import 'package:my_shop/app/services/api_client.dart';

void main() {
  late DioAdapter adapter;

  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    Get.testMode = true;
    Get.put(ConnectionManagerController());
    adapter = DioAdapter(dio: BaseClient.dio);
  });

  tearDown(Get.reset);

  test('loading -> success with parsed users', () async {
    adapter.onGet('/users', (server) => server.reply(200, [
          {'id': 1, 'name': 'Leanne', 'username': 'Bret', 'email': 'l@example.com'},
        ]));

    final controller = UsersController();
    final seen = <ApiCallStatus>[];
    ever(controller.apiCallStatus, seen.add);

    await controller.loadUsers();

    expect(seen, [ApiCallStatus.loading, ApiCallStatus.success]);
    expect(controller.users.single.name, 'Leanne');
  });

  test('server error -> error status with message', () async {
    adapter.onGet('/users', (server) => server.reply(500, {'message': 'boom'}));

    final controller = UsersController();
    await controller.loadUsers();

    expect(controller.apiCallStatus.value, ApiCallStatus.error);
    expect(controller.errorMessage.value, 'boom');
  });
}
```

Constructing the controller directly (not via `Get.put`) means `onInit` does
not run, so the test controls exactly when `loadUsers` fires.

## Widget test of a real route

`test/widget_test.dart` in the scaffold boots `GetMaterialApp` with the real
`AppPages.routes`, `InitialBinding`, themes and translations, then taps the
counter. Copy its `buildTestApp()` helper and change `initialRoute` to test
another screen.

## Language switch test

`LocalizationService.updateLanguage` skips `Get.updateLocale` when
`Get.testMode` is true. To test the real switch, leave test mode off and run
the call outside FakeAsync, because `Get.updateLocale` forces an app
reassemble that the test binding rejects inside `testWidgets`' fake clock
(`scheduleWarmUpFrame` assertion):

```dart
Get.testMode = false;
// ...pump the app...
await tester.runAsync(LocalizationService.toggleLanguage);
await tester.pumpAndSettle();
expect(find.text('مرحباً!'), findsOneWidget);
expect(Directionality.of(tester.element(find.text('مرحباً!'))), TextDirection.rtl);
```

See `test/locale_switch_test.dart` in the scaffold.

## Hive test

```dart
setUpAll(() async {
  tempDir = await Directory.systemTemp.createTemp('hive_test');
  await MyHive.init(
    testPath: tempDir.path,
    registerAdapters: (hive) => hive.registerAdapter(UserModelAdapter()),
  );
});

tearDownAll(() async {
  await Hive.close();
  await tempDir.delete(recursive: true);
});
```

## Model round-trip

For every model generated from a JSON sample, assert
`jsonEncode(Model.fromJson(raw).toJson()) == jsonEncode(raw)` against the
sample in `assets/models/`.

## Before finishing any change

```bash
flutter analyze   # must report "No issues found!"
flutter test      # must report "All tests passed!"
```
