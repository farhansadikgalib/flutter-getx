---
description: Add a GetX page (binding, controller, view, route) using get_cli and the project's base classes
argument-hint: '<name> [--on <parent_module>]'
---

Add a page to the current GetX project. Arguments: $ARGUMENTS

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`.

1. Normalize the name to snake_case (`Product Detail` becomes `product_detail`). If no name was given, ask.
2. Run from the project root:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/new_module.py" <name> [--on <parent>]
   ```

   It refuses if the module exists, runs `get create page` (or bundled templates without get_cli), converts the controller to `BaseController` and the view to `BaseView`, and checks the route.
3. If the user described what the page should show, implement it now in the generated controller and view, following `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/state-management.md`. Put user-visible text in locales with `/flutter-getx:string`.
4. Run `flutter analyze` and fix anything it reports.
5. Report the files, the route (`Routes.<NAME>`), and how to navigate: `Get.toNamed(Routes.<NAME>)`.
