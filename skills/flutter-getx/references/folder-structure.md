# Folder structure and file placement

The layout follows
[Flutter-GetX-with-Basic-Setup](https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup).
Decide where a file goes with the table at the bottom before creating it.

```
lib/
├── main.dart                       # init Hive + SharedPreferences, ScreenUtilInit, GetMaterialApp
├── generated/
│   └── locales.g.dart              # get generate locales output (do not edit)
├── app/
│   ├── components/                 # shared widgets used by 2+ modules
│   │   ├── api_error_widget.dart
│   │   ├── custom_loading_overlay.dart
│   │   ├── custom_snackbar.dart
│   │   └── my_widgets_animator.dart
│   ├── core/
│   │   ├── base/                   # BaseController, BaseView, PageState
│   │   ├── binding/                # InitialBinding (app-wide services)
│   │   └── connection_manager/     # connectivity controller + binding
│   ├── data/
│   │   ├── local/                  # MyHive, MySharedPref
│   │   ├── models/                 # DTOs / Hive objects (+ generated *.g.dart)
│   │   └── remote/                 # one data source per backend resource
│   ├── modules/                    # one folder per screen (get_cli pages)
│   │   └── home/
│   │       ├── bindings/home_binding.dart
│   │       ├── controllers/home_controller.dart
│   │       └── views/home_view.dart
│   ├── routes/
│   │   ├── app_pages.dart          # GetPage list (get_cli edits this)
│   │   └── app_routes.dart         # Routes / _Paths constants (get_cli edits this)
│   └── services/                   # BaseClient (Dio), ApiException, ApiCallStatus
├── config/
│   ├── theme/                      # MyTheme, MyStyles, MyFonts, palettes, ThemeExtensions
│   └── translations/               # LocalizationService
└── utils/                          # Constants, pure helpers
assets/
├── images/  vectors/  lottie/
├── locales/                        # en_US.json, ar_AR.json (source of all strings)
└── models/                         # JSON samples for json_to_model.py (not bundled in the app)
test/
```

## Naming

| Thing | File | Class |
|---|---|---|
| Module `product_detail` | `modules/product_detail/` | |
| Controller | `controllers/product_detail_controller.dart` | `ProductDetailController extends BaseController` |
| View | `views/product_detail_view.dart` | `ProductDetailView extends BaseView<ProductDetailController>` |
| Binding | `bindings/product_detail_binding.dart` | `ProductDetailBinding extends Bindings` |
| Route | `app_routes.dart` | `Routes.PRODUCT_DETAIL` = `'/product-detail'` |
| Model | `data/models/product_model.dart` | `ProductModel` |
| Remote source | `data/remote/product_remote_source.dart` | `ProductRemoteSource` |
| Theme extension | `config/theme/theme_extensions/<name>_theme_data.dart` | `<Name>ThemeData extends ThemeExtension` |

Route constants are SCREAMING_CASE because get_cli generates them;
`analysis_options.yaml` disables `constant_identifier_names` for that reason.

## Where does it go?

| You are adding | Put it in |
|---|---|
| A new screen | `modules/<name>/` via `scripts/new_module.py <name>` |
| A sub-screen only reachable from another screen | `modules/<parent>/<name>/` via `new_module.py <name> --on <parent>` |
| A widget used by one screen | `modules/<name>/views/widgets/` |
| A widget used by several screens | `app/components/` |
| An HTTP call | a method on a source in `data/remote/` that calls `BaseClient.safeApiCall` |
| JSON model | `data/models/` via `scripts/json_to_model.py` |
| Something cached on disk | a box in `data/local/my_hive.dart`; small flags in `my_shared_pref.dart` |
| An app-wide service (auth session, analytics) | a `GetxService` registered in `core/binding/initial_binding.dart` |
| A color or text style | `config/theme/` palettes and `MyStyles`, never inline hex in a view |
| A user-visible string | `assets/locales/*.json`, then `get generate locales assets/locales` |
| A base URL, timeout, key name | `utils/constants.dart` |

## Example: a remote source (from the templates)

```dart
class UserRemoteSource {
  Future<void> fetchUsers({
    required FutureOr<void> Function(List<UserModel> users) onSuccess,
    required FutureOr<void> Function(ApiException exception) onError,
  }) {
    return BaseClient.safeApiCall(
      '/users',
      RequestType.get,
      onSuccess: (response) {
        final list = (response.data as List<dynamic>)
            .map((e) => UserModel.fromJson(e as Map<String, dynamic>))
            .toList();
        return onSuccess(list);
      },
      onError: onError,
    );
  }
}
```
