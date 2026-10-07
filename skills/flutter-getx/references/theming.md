# Theming

Files in `lib/config/theme/`:

| File | Holds |
|---|---|
| `light_theme_colors.dart`, `dark_theme_colors.dart` | Palettes. Same constant names in both. |
| `my_fonts.dart` | Font family per language and every size in `.sp` |
| `my_styles.dart` | Component themes (`AppBarThemeData`, `ElevatedButtonThemeData`, `TextTheme`, chips, list tiles) and theme extensions |
| `my_theme.dart` | Builds `ThemeData` for light/dark, persists and switches the mode |
| `theme_extensions/` | Custom `ThemeExtension`s for values Material has no slot for |

## How switching works

`main.dart` passes both themes and the saved mode:

```dart
GetMaterialApp(
  theme: MyTheme.light(),
  darkTheme: MyTheme.dark(),
  themeMode: MyTheme.themeMode, // from SharedPreferences
  ...
)
```

`MyTheme.changeTheme()` flips the flag in SharedPreferences and calls
`Get.changeThemeMode(...)`, so the choice survives restarts. Read the current
mode with `Get.isDarkMode` in views.

Build themes inside `ScreenUtilInit`'s builder (as `main.dart` does). The
styles use `.sp` / `.r`, which need ScreenUtil initialized.

## Changing the look

1. Edit the palette constants; keep names identical across light and dark.
2. Add a new color to both palettes, then read it in `MyStyles`, not in views.
3. In views use `Theme.of(context).colorScheme.*`, `textTheme.*`, or an
   extension. No hex literals in `modules/`.

`MyTheme.getThemeData` builds an explicit `ColorScheme`:

```dart
final colorScheme = ColorScheme(
  brightness: isLight ? Brightness.light : Brightness.dark,
  primary: isLight ? LightThemeColors.primaryColor : DarkThemeColors.primaryColor,
  onPrimary: isLight ? Colors.white : Colors.black,
  secondary: isLight ? LightThemeColors.accentColor : DarkThemeColors.accentColor,
  onSecondary: isLight ? Colors.black : Colors.white,
  error: isLight ? LightThemeColors.errorColor : DarkThemeColors.errorColor,
  onError: Colors.white,
  surface: isLight ? LightThemeColors.backgroundColor : DarkThemeColors.backgroundColor,
  onSurface: isLight ? LightThemeColors.bodyTextColor : DarkThemeColors.bodyTextColor,
);
```

Prefer `ColorScheme.fromSeed(seedColor: ...)` if the design has a single brand
color and no fixed palette.

## Adding a ThemeExtension

```dart
class BadgeThemeData extends ThemeExtension<BadgeThemeData> {
  const BadgeThemeData({this.color});
  final Color? color;

  @override
  BadgeThemeData copyWith({Color? color}) => BadgeThemeData(color: color ?? this.color);

  @override
  BadgeThemeData lerp(covariant ThemeExtension<BadgeThemeData>? other, double t) {
    if (other is! BadgeThemeData) return this;
    return BadgeThemeData(color: Color.lerp(color, other.color, t));
  }
}
```

Register it in `MyTheme.getThemeData`'s `extensions:` list via a
`MyStyles.getBadgeTheme(isLightTheme:)` getter, and read it with
`Theme.of(context).extension<BadgeThemeData>()?.color`.

## Responsive sizes

`flutter_screenutil` scales from the artboard set in `main.dart`
(`designSize`, default 375x812, set via `scaffold.py --design-size`).

| Use | For |
|---|---|
| `16.w` / `16.h` | widths / heights from the design |
| `14.sp` | font sizes (already used by `MyFonts`) |
| `8.r` | radii |
| `12.verticalSpace` / `8.horizontalSpace` | gaps |

`main.dart` wraps the app in `MediaQuery.withNoTextScaling` so the OS font
size does not distort the design. Remove that wrapper if accessibility
scaling matters more than pixel fidelity for your app.

## Deprecated APIs to avoid

| Avoid | Use |
|---|---|
| `MaterialStateProperty`, `MaterialState` | `WidgetStateProperty`, `WidgetState` |
| `color.withOpacity(x)` | `color.withValues(alpha: x)` |
| `ColorScheme.fromSwatch` | `ColorScheme(...)` or `ColorScheme.fromSeed` |
| `AppBarTheme(...)` in `ThemeData.appBarTheme` | `AppBarThemeData(...)` |
| `CardTheme(...)` | `CardThemeData(...)` |
| `SvgPicture.asset(p, color: c)` | `colorFilter: ColorFilter.mode(c, BlendMode.srcIn)` |
| `textScaleFactor` | `TextScaler` / `MediaQuery.withNoTextScaling` |
