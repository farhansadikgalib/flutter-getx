# State management with GetX

## Pick the tool

| Use | When | Rebuilds |
|---|---|---|
| `.obs` + `Obx(() => ...)` | Default. Any value the view shows that changes over time. | Only the `Obx` that read the value. |
| `GetBuilder<C>` + `update()` | Large lists or objects you mutate in place many times per second, or when you want to batch several changes into one rebuild. | Every `GetBuilder<C>` (or one `id`). |
| Plain field | Values set once in `onInit` that never change on screen. | Never. |
| `ever` / `debounce` / `interval` workers | Side effects when an `.obs` changes (save, search-as-you-type). | n/a |

Rules that keep this predictable:

* Controllers own state. Views read it and call controller methods; they never
  hold `.obs` themselves.
* Wrap the smallest widget that needs the value in `Obx`. `BaseView` already
  wraps the scaffold in an `Obx` for `resizeToAvoidBottomInset`; do not put
  your whole `body` inside another `Obx` unless every part of it is reactive.
* An `Obx` must read at least one `.obs` synchronously in its builder, or GetX
  throws "improper use of GetX". Reading inside a callback does not count.
* Use `.assignAll` / `.add` on `RxList` and `.value =` on `Rx<T>`. Mutating a
  field of an object inside `Rx<T>` needs `.refresh()`.
* Extend `BaseController`, not `GetxController`, so `pageState`, `logger` and
  `connection` are available.

## Reactive example (from the scaffold's home module)

```dart
class HomeController extends BaseController {
  final count = 0.obs;

  void increment() => count.value++;
}

// in HomeView.body
Obx(
  () => Text(
    LocaleKeys.counter_label.trParams({'count': '${controller.count.value}'}),
  ),
)
```

## GetBuilder example

```dart
class CartController extends BaseController {
  final List<CartItem> items = [];

  void add(CartItem item) {
    items.add(item);
    update(['cart_total']); // rebuild only builders with this id
  }
}

GetBuilder<CartController>(
  id: 'cart_total',
  builder: (c) => Text('${c.items.length} items'),
)
```

## Async loading: ApiCallStatus

For anything fetched from the network keep one `Rx<ApiCallStatus>` per
independently loading region and render it with `MyWidgetsAnimator`. See
`networking.md` for the full controller and view.

```dart
final apiCallStatus = ApiCallStatus.holding.obs;
```

| Status | Meaning |
|---|---|
| `holding` | nothing requested yet |
| `loading` | first load, show a spinner or shimmer |
| `success` / `cache` | data ready |
| `empty` | request succeeded with no data |
| `error` | show `ApiErrorWidget` with retry |
| `refresh` | reloading with data already on screen |

## Page-level state: PageState

`BaseController.pageState` covers whole-page situations (`loading`,
`unauthorized`, `noInternet`, ...). Use `showLoading()` / `hideLoading()` for a
blocking action such as submitting a form, or `showLoadingOverLay(asyncFunction: ...)`
from `components/custom_loading_overlay.dart` to block input until it ends.

## Workers

```dart
@override
void onInit() {
  super.onInit();
  debounce(query, (_) => search(), time: const Duration(milliseconds: 400));
}
```

Workers created in `onInit` are disposed with the controller.

## Lifecycle

| Hook | Runs | Use for |
|---|---|---|
| `onInit` | right after creation | start loading, set up workers |
| `onReady` | one frame after the view is on screen | dialogs, navigation, snackbars |
| `onClose` | when the route is removed | cancel streams, dispose `TextEditingController`s |

Do not override a hook just to call `super`; the `unnecessary_overrides` lint
flags it.
