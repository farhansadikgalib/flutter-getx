# Spec Delta

## Purpose

Defines one get_cli-style command grammar for every flutter-getx operation. Humans, Claude Code slash commands and other agents all use the same verbs, targets and modifiers and get the same results.

## ADDED Requirements

### Requirement: get_cli-style grammar
The interface SHALL accept commands of the form `<verb> [<target>:<name>] [on <module>] [with <source>] [flags]`, with verbs `create`, `generate`, `init`, `install`, `upgrade`, `doctor`, and `help`. Names SHALL be normalised to snake_case.

#### Scenario: Create a page like get_cli
- **WHEN** the user runs `getx create page:cart`
- **THEN** a `cart` module with binding, controller (extending BaseController), view (extending BaseView) and route is created, as `get create page:cart` would, and the command exits 0

#### Scenario: Nested target with on
- **WHEN** the user runs `getx create page:reviews on product_detail`
- **THEN** the page is created inside `product_detail` and registered as a child route

#### Scenario: Name normalisation
- **WHEN** the user runs `getx create page:"Order History"`
- **THEN** the module is created as `order_history`

### Requirement: create targets
`create` SHALL support the targets `project`, `page`, `controller`, `view`, `feature`, and `string`. `controller` and `view` SHALL require `on <module>`, conform to the base classes, and register a controller in that module's binding.

#### Scenario: New project
- **WHEN** the user runs `getx create project:my_shop --platforms android,ios`
- **THEN** a project is created with the folder pattern and latest packages, and `flutter analyze` and `flutter test` pass

#### Scenario: Controller on an existing module
- **WHEN** the user runs `getx create controller:edit on profile`
- **THEN** `edit_controller.dart` extends BaseController, `profile_binding.dart` registers `EditController`, and `flutter analyze` reports no issues

#### Scenario: Missing on for controller
- **WHEN** the user runs `getx create controller:edit` without `on`
- **THEN** the command exits non-zero with a message that `on <module>` is required, and no files change

#### Scenario: Translated string
- **WHEN** the user runs `getx create string:checkout "Checkout" --ar "الدفع"`
- **THEN** every locale file gains `checkout` and `LocaleKeys.checkout` is regenerated

### Requirement: generate targets
`generate` SHALL support `model:<ClassName> with <json-file|url>` (optional `on <module>` to place it under that module) and `locales`.

#### Scenario: Model from a URL
- **WHEN** the user runs `getx generate model:Customer with https://example.com/users/1`
- **THEN** the sample is saved under `assets/models/` and `lib/app/data/models/customer_model.dart` is written with nested classes

#### Scenario: Locales
- **WHEN** the user runs `getx generate locales`
- **THEN** `lib/generated/locales.g.dart` is regenerated from `assets/locales/*.json`

### Requirement: Other verbs map to existing behaviour
`init`, `install <package|fcm>`, `upgrade` and `doctor` SHALL perform the existing init, add-package, Firebase add-on, upgrade and doctor behaviour. `install <package>` SHALL add the latest stable pub.dev version.

#### Scenario: Install a package
- **WHEN** the user runs `getx install lottie`
- **THEN** `lottie` is added to pubspec at its latest stable version and `flutter pub get` runs

#### Scenario: Install the Firebase add-on
- **WHEN** the user runs `getx install fcm`
- **THEN** the FCM add-on is applied and the project still passes `flutter analyze`

### Requirement: Help and discoverability
`getx help` and `getx help <verb>` SHALL print the grammar, every target and an example for each. An unknown verb or target SHALL print the closest valid form.

#### Scenario: Typo
- **WHEN** the user runs `getx creat page:cart`
- **THEN** the command exits non-zero and suggests `getx create page:cart`

### Requirement: Safe and predictable execution
Every command that writes files SHALL support `--dry-run` (list the planned changes, write nothing). Commands SHALL never overwrite user-edited files. Commands SHALL exit 0 on success, 1 on a failed operation, and 2 on invalid usage.

#### Scenario: Dry run
- **WHEN** the user runs `getx create page:cart --dry-run`
- **THEN** the planned files and route changes are printed and the project tree is unchanged

#### Scenario: Existing module
- **WHEN** the user runs `getx create page:home` and `home` exists
- **THEN** the command exits 1 with "already exists" and no files change

### Requirement: Slash commands use the same grammar
The Claude Code plugin SHALL expose `/flutter-getx:create`, `/flutter-getx:generate`, `/flutter-getx:init`, `/flutter-getx:install`, `/flutter-getx:upgrade`, and `/flutter-getx:doctor`. Each SHALL accept the same arguments as the matching `getx` verb and run it, then do the judgment work the CLI cannot (implementing described behaviour, fixing analyzer output).

#### Scenario: Slash command parity
- **WHEN** a user types `/flutter-getx:create page:cart on home` in Claude Code
- **THEN** the result matches `getx create page:cart on home` run in a terminal

#### Scenario: Described page
- **WHEN** a user types `/flutter-getx:create page:profile showing the saved user's email with a logout button`
- **THEN** the page is created with `getx`, and Claude then implements the described behaviour so `flutter analyze` passes
