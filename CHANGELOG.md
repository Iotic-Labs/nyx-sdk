# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 18/10/2024

*Breaking changes included*

- Nyx SDK is now two packages `nyx-client` for simple API interactions, and `nyx-extras` for AI specific tooling

- `Data` now takes more arguments, matching what is in the UI

- `Data` no longer has method `download()` use `as_string()` or `as_bytes()` if it's a binary

- All configs; `BaseNyxConfig` and `NyxConfigExtended` (Replaces `OpenAiNyxConfig` and `CohereNyxConfig`) are now
  constructed from params by default, old functionality is exposed via `BaseNyxConfig.from_env()`

- `NyxClient` most methods to retrieve data have been replaced in preference of `get_data()` that supports multiple
  combined filters. `get_categories()` and other property lists have been replaced with `categories()` (etc)

- `NyxClient` now supports `subscribe()`, `unsubscribe()` and `update_data()`

- `NyxClient` is now only initalized with an optional `BaseNyxConfig`, and no-longer takes an `env_file`

- `NyxLangChain` has moved to package `nyx-extras`, and no longer takes an `env_file`

- `Parser` has moved to package `nyx-extras`

## [0.1.3] - 27/09/2024

- fix: EI-3331 - Bump iotics-identity to 2.1.2 for security [#15](https://github.com/Iotic-Labs/nyx-sdk/pull/15)

- feat: allow download in bytes [#11](https://github.com/Iotic-Labs/nyx-sdk/pull/11)

- feat: ei-3339 change highlevel example default to openai [#16](https://github.com/Iotic-Labs/nyx-sdk/pull/16)

- fix: EI-3364 - NyxClient.get_data_for_creators creator not returned [#18](https://github.com/Iotic-Labs/nyx-sdk/pull/18)

- fix: EI-3364 - NyxClient.get_subscribed_categories query error

## [0.1.2] - 23/09/2024

- bug: upper casing can break AI when looking for sources [#13](https://github.com/Iotic-Labs/nyx-sdk/pull/13)

## [0.1.1] - 20/09/2024

- fix: override default sample rows; set to 0; plays havoc with getting a defined list of subscriptions [#7](https://github.com/Iotic-Labs/nyx-sdk/pull/7)

- bug: json/excel parsing has invalid param [#7](https://github.com/Iotic-Labs/nyx-sdk/pull/7)

## [0.1.0] - 19/09/2024

- Initial public release
