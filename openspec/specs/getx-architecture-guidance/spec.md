# getx-architecture-guidance Specification

## Purpose
Defines the reference guidance the skill carries so Claude writes idiomatic, version-current GetX code on top of the scaffold instead of relying on outdated training knowledge.

## Requirements

### Requirement: Reference material covers each architectural layer
The skill SHALL provide reference documents for: folder pattern and file placement, GetX state management and dependency injection, navigation and bindings, networking with the safe client, theming, localization, local storage, get_cli usage, package versions with migration notes, and the Firebase add-on.

#### Scenario: Layer lookup
- **WHEN** Claude must decide where a new repository class belongs
- **THEN** the folder-pattern reference names the directory and the naming convention for it

#### Scenario: State management choice
- **WHEN** Claude must choose between reactive `.obs`/`Obx` and `GetBuilder`/`update()`
- **THEN** the state management reference states when each is appropriate and shows one example of each

### Requirement: Migration notes reflect the pinned versions
The package reference SHALL list, for each dependency, the pinned version, the reason it is used, and any breaking API changes relative to the reference repo's original version, including replacements for deprecated Flutter APIs used by the templates.

#### Scenario: Deprecated API avoided
- **WHEN** Claude writes a button theme or text scaling code
- **THEN** the reference directs it to `WidgetStateProperty` and `TextScaler` rather than `MaterialStateProperty` and `textScaleFactor`

#### Scenario: Connectivity stream shape
- **WHEN** Claude subscribes to connectivity changes
- **THEN** the reference shows the list-based result type used by connectivity_plus 6+ and the handling of multiple simultaneous results

### Requirement: Guidance includes worked examples
Each reference document SHALL include at least one complete, compilable example drawn from the templates, so Claude can copy patterns rather than invent them.

#### Scenario: API-backed feature
- **WHEN** the user asks for a screen that lists items from a REST endpoint
- **THEN** the networking reference provides an example controller that uses the safe client, sets call status, maps the response to a model, and a view that renders it through the widget animator

### Requirement: Guidance states testing conventions
The reference material SHALL describe how to unit test controllers and the API client (mock adapter, test mode for GetX, Hive test path) and where tests live.

#### Scenario: Controller test
- **WHEN** Claude adds a controller with an API call
- **THEN** the guidance shows how to inject the mock adapter and assert the call status transitions
