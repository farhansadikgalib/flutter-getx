---
description: Build an API-backed screen end to end - model, remote source, controller with loading/error/empty states, view, route, and tests
argument-hint: '<name> <endpoint_url_or_path> [sample.json]'
---

Build an API-backed feature in the current GetX project. Arguments: $ARGUMENTS

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`. Read `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/networking.md` and `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/testing.md` before writing code; mirror the structure of its users-list example.

1. You need a feature name, an endpoint, and a JSON sample of one item. If the sample is missing, fetch the endpoint once to get one; if that fails, ask the user for a sample.
2. Save the sample to `assets/models/<name>.json` and generate the model:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/json_to_model.py" assets/models/<name>.json <Name>Model
   ```

   Mark fields the API may omit with `--nullable a,b`. Name the model after one item in singular form: `products` gives `ProductModel` and `product_model.dart`.
3. Create the page: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/new_module.py" <name>`.
4. Write `lib/app/data/remote/<name>_remote_source.dart` calling `BaseClient.safeApiCall`. A full URL in the call overrides `Constants.baseUrl`; otherwise add the path relative to it.
5. Write the controller (`Rx<ApiCallStatus>`, list, error message, `load({bool refresh})`) and the view (`MyWidgetsAnimator` with loading, `ApiErrorWidget` retry, empty state, `RefreshIndicator`).
6. Add user-visible strings with `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/add_string.py"`.
7. Add `test/<name>_controller_test.dart` with `http_mock_adapter`: loading to success, server error, empty list.
8. Run `flutter analyze` and `flutter test`; fix until both pass.
9. Report the files, the route, and the test results.
