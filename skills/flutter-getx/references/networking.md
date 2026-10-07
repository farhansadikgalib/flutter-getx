# Networking with BaseClient

`lib/app/services/api_client.dart` wraps Dio. Every call ends in exactly one
of `onSuccess` or `onError`; nothing throws out of `safeApiCall`. The pieces:

| File | Role |
|---|---|
| `services/api_client.dart` | `BaseClient.safeApiCall`, `BaseClient.download`, shared `Dio` with base URL, timeouts, `PrettyDioLogger` in debug |
| `services/api_exceptions.dart` | `ApiException(url, message, statusCode, response)`; `toString()` prefers the server's `message`/`error` field |
| `services/api_call_status.dart` | `ApiCallStatus` enum for the UI |
| `data/remote/*_remote_source.dart` | one class per backend resource; parses JSON into models |
| `components/my_widgets_animator.dart` | renders loading / success / error / empty by status |
| `utils/constants.dart` | `Constants.baseUrl` (defaults to jsonplaceholder so the scaffold runs) |

## Error mapping

| Situation | `ApiException.message` (localized) | `statusCode` |
|---|---|---|
| connect/send/receive/transform timeout | `server_not_responding` | null |
| no connection | `no_internet_connection` | null |
| 401 / 403 | `unauthorized` | 401 / 403 |
| 404 | `url_not_found` | 404 |
| 5xx | `server_error` | 5xx |
| other HTTP error | Dio message | code |
| exception inside `onSuccess` (bad JSON) | `unexpected_error` (stack trace logged) | null |

If no `onError` is passed, an error toast is shown instead.

## Full example: list screen backed by an API

Verified to compile and pass its tests against a fresh scaffold.

### Remote source (`data/remote/user_remote_source.dart`, in the templates)

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

### Controller (`modules/users/controllers/users_controller.dart`)

```dart
import 'package:get/get.dart';

import 'package:my_shop/app/core/base/base_controller.dart';
import 'package:my_shop/app/data/models/user_model.dart';
import 'package:my_shop/app/data/remote/user_remote_source.dart';
import 'package:my_shop/app/services/api_call_status.dart';

class UsersController extends BaseController {
  /// The source is injectable so tests can pass a fake.
  UsersController({UserRemoteSource? source})
      : _source = source ?? UserRemoteSource();

  final UserRemoteSource _source;

  final apiCallStatus = ApiCallStatus.holding.obs;
  final users = <UserModel>[].obs;
  final errorMessage = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadUsers();
  }

  Future<void> loadUsers({bool refresh = false}) async {
    // Keep the current list on screen while refreshing.
    apiCallStatus.value = refresh ? ApiCallStatus.refresh : ApiCallStatus.loading;
    await _source.fetchUsers(
      onSuccess: (result) {
        users.assignAll(result);
        apiCallStatus.value =
            result.isEmpty ? ApiCallStatus.empty : ApiCallStatus.success;
      },
      onError: (exception) {
        errorMessage.value = exception.toString();
        apiCallStatus.value = ApiCallStatus.error;
      },
    );
  }
}
```

### View (`modules/users/views/users_view.dart`)

```dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'package:my_shop/app/components/api_error_widget.dart';
import 'package:my_shop/app/components/my_widgets_animator.dart';
import 'package:my_shop/app/core/base/base_view.dart';
import '../controllers/users_controller.dart';

class UsersView extends BaseView<UsersController> {
  const UsersView({super.key});

  @override
  PreferredSizeWidget? appBar(BuildContext context) =>
      AppBar(title: const Text('Users'));

  @override
  Widget body(BuildContext context) {
    return Obx(
      () => MyWidgetsAnimator(
        apiCallStatus: controller.apiCallStatus.value,
        loadingWidget: () => const Center(child: CircularProgressIndicator()),
        errorWidget: () => ApiErrorWidget(
          message: controller.errorMessage.value,
          retryAction: controller.loadUsers,
        ),
        emptyWidget: () => const Center(child: Text('No users yet')),
        successWidget: () => RefreshIndicator(
          onRefresh: () => controller.loadUsers(refresh: true),
          child: ListView.separated(
            itemCount: controller.users.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (_, index) {
              final user = controller.users[index];
              return ListTile(
                title: Text(user.name),
                subtitle: Text(user.email),
              );
            },
          ),
        ),
      ),
    );
  }
}
```

Replace `my_shop` with the project's package name.

## POST with a body

```dart
Future<void> createPost(
  PostModel post, {
  required FutureOr<void> Function(PostModel created) onSuccess,
  required FutureOr<void> Function(ApiException e) onError,
}) {
  return BaseClient.safeApiCall(
    '/posts',
    RequestType.post,
    data: post.toJson(),
    onSuccess: (r) => onSuccess(PostModel.fromJson(r.data as Map<String, dynamic>)),
    onError: onError,
  );
}
```

Use `showLoadingOverLay(asyncFunction: () => source.createPost(...))` to block
the UI while it runs.

## Auth header

Add an interceptor once at startup (for example in `InitialBinding` or after
login):

```dart
BaseClient.dio.interceptors.add(
  InterceptorsWrapper(
    onRequest: (options, handler) {
      final token = MySharedPref.getAuthToken(); // add this getter to MySharedPref
      if (token != null) options.headers['Authorization'] = 'Bearer $token';
      handler.next(options);
    },
  ),
);
```

## Do not

* Do not call `Dio()` or `http` directly from controllers; go through a remote
  source so errors stay typed and localized.
* Do not use get_cli's `GetConnect` providers; they bypass `BaseClient`.
* Do not parse JSON in the view.
* Do not import `package:get/get.dart` and `package:dio/dio.dart` in the same
  file without hiding one `Response`: both export it and the analyzer reports
  `ambiguous_import`. Use `import 'package:get/get.dart' hide Response;`, or
  import only `package:get/get_utils/get_utils.dart` when you just need `.tr`
  (as `api_client.dart` does).

## Platform permissions

`scripts/scaffold.py` adds the INTERNET permission to Android's main manifest
and the `com.apple.security.network.client` entitlement on macOS. Without them,
release Android builds and all macOS builds fail every request.
