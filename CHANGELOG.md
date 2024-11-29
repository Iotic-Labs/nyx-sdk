# Versions

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2024-??-??

- Introduce (optional) support for setting custom metadata (properties) on `Data` instances. See `custom_metadata` parameter documentation for `NyxClient.create_data()`. The `nyx_client.properties` module contains helpers for creating properties. An example:
    ```python
    client.create_data(
        "my_dataset",
        ...,
        custom_metadata=[
            Property.lang_string(SOME_NAMESPACE+"pred1", "good morning", "en"),
            Property.string(SOME_NAMESPACE+"pred2", "plain string"),
            Property.literal(SOME_NAMESPACE+"pred3", b64encode(b"binary blob").decode("ascii"), "base64Binary"),
            Property.uri(RDF_TYPE, NS+"SomeClass"),
        ],
    )
    ```

## [0.2.4] - 2024-11-20

### Changed
- Configuration (env) files are now found **relative to the current working directory** instead of `nyx_client`
  installation directory. (There is no change if the configuration file has been specified using an absolute path.)
- `env_file` for `BaseNyxConfig.from_env` and `NyxConfigExtended.from_env` is still optional but now defaults to `.env`
  (instead of `None`), to clearly illustrate what the default search path will be.

## [0.2.3] - 2024-11-14

### Added
- `Circle` object added, along side methods on `NyxClient` to get, create, update and delete circles, to enabled
   selective sharing of data
- `NyxClient.create_data` now creates data privately by default. Additional parameters of `circles` and `access_control`
  have been added, to enable selective sharing of the data

## [0.2.2] - 2024-11-6

### Fixed
- `NyxClient.create_data` had a bug where the download url was sent to the API in an incorrect format.

## [0.2.1] - 2024-10-31

### Changed
- `NyxClient.create_data` and `NyxClient.update_data` now make size and download url optional

### Added
- `NyxClient.create_data` and `NyxClient.update_data` now support a passing a file to be uploaded
  either a file, or a download_url must be provided

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
