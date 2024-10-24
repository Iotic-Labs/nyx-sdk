# Versions

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-10-18

### Changed

- Nyx SDK is now two packages `nyx-client` for simple API interactions, and `nyx-extras` for AI specific tooling
- `Data` now takes more arguments, matching what is in the UI
- All configs; `BaseNyxConfig` and `NyxConfigExtended` (Replaces `OpenAiNyxConfig` and `CohereNyxConfig`) are now constructed from params by default, old functionality is exposed via `BaseNyxConfig.from_env()`
- `NyxClient` most methods to retrieve data have been replaced in preference of `get_data()` that supports multiple combined filters
- `NyxClient` is now only initalized with an optional `BaseNyxConfig`, and no-longer takes an `env_file`
- `NyxClient.get_data_by_name` has been renamed to `get_my_data_by_name`

### Removed

- `Data` no longer has method `download()` use `as_string()` or `as_bytes()` if it's a binary
- `NyxClient` property lists like `get_categories()` have been replaced with `categories()` (etc)

### Added

- `NyxClient` now supports `subscribe()`, `unsubscribe()` and `update_data()`

### Moved

- `NyxLangChain` has moved to package `nyx-extras`, and no longer takes an `env_file`
- `Parser` has moved to package `nyx-extras`

## [0.1.3] - 2024-09-27

### Fixed

- EI-3331 - Bump iotics-identity to 2.1.2 for security ([#15](https://github.com/Iotic-Labs/nyx-sdk/pull/15))
- EI-3364 - NyxClient.get_data_for_creators creator not returned ([#18](https://github.com/Iotic-Labs/nyx-sdk/pull/18))
- EI-3364 - NyxClient.get_subscribed_categories query error

### Added

- Allow download in bytes ([#11](https://github.com/Iotic-Labs/nyx-sdk/pull/11))

### Changed

- EI-3339 change highlevel example default to openai ([#16](https://github.com/Iotic-Labs/nyx-sdk/pull/16))

## [0.1.2] - 2024-09-23

### Fixed

- Upper casing can break AI when looking for sources ([#13](https://github.com/Iotic-Labs/nyx-sdk/pull/13))

## [0.1.1] - 2024-09-20

### Fixed

- Override default sample rows; set to 0; plays havoc with getting a defined list of subscriptions ([#7](https://github.com/Iotic-Labs/nyx-sdk/pull/7))
- JSON/Excel parsing has invalid param ([#7](https://github.com/Iotic-Labs/nyx-sdk/pull/7))

## [0.1.0] - 2024-09-19

### Added

- Initial public release
