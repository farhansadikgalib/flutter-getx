# Localization

All user-visible strings live in `assets/locales/<lang>_<COUNTRY>.json`.
get_cli turns them into `lib/generated/locales.g.dart`, and
`LocalizationService` feeds that to GetX.

```
assets/locales/en_US.json  ─┐
assets/locales/ar_AR.json  ─┴─ get generate locales assets/locales ─▶ lib/generated/locales.g.dart
                                                                     (AppTranslation, LocaleKeys)
```

## Add or change a string

1. Add the same key to every JSON file:

   ```json
   { "profile_title": "Profile" }
   ```

2. Regenerate:

   ```bash
   get generate locales assets/locales
   ```

3. Use it:

   ```dart
   Text(LocaleKeys.profile_title.tr)
   ```

Never hand-edit `locales.g.dart`; it is overwritten. If get_cli is
unavailable, add the key to both the `LocaleKeys` class and each `Locales`
map in that file by hand, matching the generated format, and regenerate later.

Nested JSON flattens with underscores: `{"buttons": {"login": "Login"}}`
becomes `LocaleKeys.buttons_login`.

## Parameters and plurals

```json
{ "counter_label": "Button tapped @count times" }
```

```dart
LocaleKeys.counter_label.trParams({'count': '$n'})
```

For plurals add `item` and `items` keys and use
`LocaleKeys.item.trPlural(LocaleKeys.items, count)`.

## Switching language

```dart
await LocalizationService.updateLanguage('ar'); // persists + Get.updateLocale
await LocalizationService.toggleLanguage();      // en <-> ar
LocalizationService.getCurrentLocal();           // saved Locale
```

The choice is saved in SharedPreferences and restored by `main.dart`
(`locale: MySharedPref.getCurrentLocal()`). Arabic switches the app to RTL
automatically.

## Add a language

1. Create `assets/locales/fr_FR.json` with every key.
2. `get generate locales assets/locales`.
3. Add `'fr': Locale('fr', 'FR')` to `LocalizationService.supportedLanguages`.
4. If the script needs a different font, add a case to `LocalizationService.fontFor`.

## Fonts per language

```dart
static TextStyle fontFor(String languageCode) {
  return switch (languageCode) {
    'ar' => GoogleFonts.cairo(),
    _ => GoogleFonts.poppins(),
  };
}
```

google_fonts downloads on first use. For offline-first apps, bundle the TTFs
under `assets/fonts/`, declare them in pubspec, and return
`TextStyle(fontFamily: 'Poppins')` instead. In tests set
`GoogleFonts.config.allowRuntimeFetching = false`.

## Error messages

`BaseClient` uses these keys, so keep them in every language:
`no_internet_connection`, `server_not_responding`, `something_went_wrong`,
`unexpected_error`, `url_not_found`, `server_error`, `unauthorized`,
`request_cancelled`, plus `retry` and `loading` for the shared components.
