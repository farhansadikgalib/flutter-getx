# Navigation and dependency injection

## Routes

Routes live in `lib/app/routes/`. Add them with `getx create page:<name> [on <parent>]`,
which lets get_cli register them, rather than editing by hand.

```dart
// app_routes.dart (generated shape)
abstract class Routes {
  Routes._();
  static const HOME = _Paths.HOME;
  static const PROFILE = _Paths.PROFILE;
  static const SETTINGS = _Paths.PROFILE + _Paths.SETTINGS; // nested: /profile/settings
}

// app_pages.dart
GetPage(
  name: _Paths.PROFILE,
  page: () => const ProfileView(),
  binding: ProfileBinding(),
  children: [
    GetPage(
      name: _Paths.SETTINGS,
      page: () => const SettingsView(),
      binding: SettingsBinding(),
    ),
  ],
),
```

Change the first screen with `AppPages.INITIAL`.

## Navigating

Always navigate by route name so the page's binding runs.

| Need | Call |
|---|---|
| Push | `Get.toNamed(Routes.PROFILE)` |
| Push with data | `Get.toNamed(Routes.PROFILE, arguments: user)`; read `Get.arguments as UserModel` in the controller's `onInit` |
| Path/query params | `Get.toNamed('${Routes.PROFILE}?id=42')`; read `Get.parameters['id']` |
| Replace current | `Get.offNamed(Routes.HOME)` |
| Clear stack (after login/logout) | `Get.offAllNamed(Routes.HOME)` |
| Back with result | `Get.back(result: true)`; `final ok = await Get.toNamed(...)` |
| Dialog / bottom sheet | `Get.dialog(...)`, `Get.bottomSheet(...)` |

Avoid `Get.to(SomeView())`: it skips the binding, so `Get.find` fails.

## Middleware (auth guard)

```dart
class AuthMiddleware extends GetMiddleware {
  @override
  RouteSettings? redirect(String? route) {
    final loggedIn = MySharedPref.getFcmToken() != null; // replace with your session check
    return loggedIn ? null : const RouteSettings(name: Routes.LOGIN);
  }
}

GetPage(name: _Paths.PROFILE, page: () => const ProfileView(),
        binding: ProfileBinding(), middlewares: [AuthMiddleware()]),
```

## Dependency injection

| Scope | Register with | Where |
|---|---|---|
| One screen | `Get.lazyPut<X>(() => X())` | the module's binding |
| App-wide, lives forever | `Get.put<X>(X(), permanent: true)` or a `GetxService` | `core/binding/initial_binding.dart` |
| App-wide, recreated on demand | `Get.lazyPut<X>(() => X(), fenix: true)` | `initial_binding.dart` (used for `ConnectionManagerController`) |
| Async init (open a box, read a token) | `await Get.putAsync<X>(() => X().init())` | `main()` before `runApp` |

Resolve with `Get.find<X>()`. Inside a `BaseView<C>` use `controller`.

Pass collaborators through the constructor so tests can swap them, and give
the binding the real one:

```dart
class UsersController extends BaseController {
  UsersController({UserRemoteSource? source})
      : _source = source ?? UserRemoteSource();
  final UserRemoteSource _source;
}

class UsersBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<UsersController>(() => UsersController());
  }
}
```

## Initial binding (from the templates)

```dart
class InitialBinding extends Bindings {
  @override
  void dependencies() {
    ConnectionManagerBinding().dependencies();
  }
}
```

`BaseView` reads `controller.connection.isInternetConnected` to show the
offline banner, so this binding must stay registered on `GetMaterialApp`.
