# Local storage

Two stores, both initialized in `main()` before `runApp`:

| Store | Class | Use for |
|---|---|---|
| SharedPreferences | `data/local/my_shared_pref.dart` (`MySharedPref`) | small flags and strings: theme, locale, tokens, onboarding seen |
| Hive CE | `data/local/my_hive.dart` (`MyHive`) | objects and lists: cached user, offline data, drafts |

Do not store secrets you would not put in SharedPreferences in Hive either;
both are plain files. Use `flutter_secure_storage` for credentials.

## SharedPreferences: add a value

Add a key constant and a typed getter/setter pair:

```dart
static const String _authTokenKey = 'auth_token';

static Future<void> setAuthToken(String token) =>
    _sharedPreferences.setString(_authTokenKey, token);

static String? getAuthToken() => _sharedPreferences.getString(_authTokenKey);
```

Read synchronously anywhere after `MySharedPref.init()`.

## Hive CE: add a cached type

1. Create or generate the model (`scripts/json_to_model.py`), then annotate it.
   Each class needs a unique `typeId`; each field a unique, never-reused index.

   ```dart
   import 'package:hive_ce/hive.dart';

   part 'product_model.g.dart';

   @HiveType(typeId: 2)
   class ProductModel {
     @HiveField(0)
     final int id;
     @HiveField(1)
     final String title;

     const ProductModel({required this.id, required this.title});
   }
   ```

2. Generate the adapter:

   ```bash
   dart run build_runner build --delete-conflicting-outputs
   ```

3. Register it in `main()`:

   ```dart
   await MyHive.init(
     registerAdapters: (hive) {
       hive.registerAdapter(UserModelAdapter());
       hive.registerAdapter(ProductModelAdapter());
     },
   );
   ```

4. Open a box in `MyHive.init` and add methods next to the user ones:

   ```dart
   static late Box<ProductModel> _productBox;
   // in init(): _productBox = await Hive.openBox<ProductModel>('products');

   static Future<void> cacheProducts(List<ProductModel> items) =>
       _productBox.putAll({for (final p in items) p.id: p});

   static List<ProductModel> cachedProducts() => _productBox.values.toList();
   ```

Changing a model later: add fields with new indexes, never renumber or reuse
an index, or existing users' data will not decode.

## Imports

hive_ce replaces the unmaintained `hive`. Import paths:

| Need | Import |
|---|---|
| annotations, `Box`, `Hive.init` | `package:hive_ce/hive.dart` |
| `Hive.initFlutter()` | `package:hive_ce_flutter/hive_flutter.dart` |

## Tests

`MyHive.init(testPath: dir.path, ...)` skips the Flutter path provider, and
`MySharedPref.setStorage(...)` accepts a mocked instance. See `testing.md`.
