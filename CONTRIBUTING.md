# Contributing

## How to contribute

If you're looking to contribute, feel free to check out the issues section on Github. Alternatively a great way to start is by raising any issues that you may have encountered here!

## Contributing code

### Setup
1. Fork and clone the repository:
   ```shell
   git clone https://github.com/<your_user>/nyx-sdk.git
   cd nyx-sdk
   ```

2. Install the package in development mode
   ```shell
   cd nyx_extras
   make setup-poetry install
   ```
   **Notes**:
      - This will also install optional extras (such as `langchain-openai`).
      - If you only want to install `nyx-client` in development mode, use the equivalent targets in the `nyx_client` directory instead.

   or if building with NyxLangChain install with

3. Create a .env file with `nyx-client init`, this will create your .env which will be picked up by nyx-sdk, containing
user details associated with your nyx instance. This file should be in the directory you are running your scripts from.

4. Start building! Running the examples, or creating your own script to test changes, and new features.
5. When you're happy with the work, raise a PR from your fork back into the nyx-sdk repo.

### Development

1. Start building! Run the examples, create your own script to test changes or add new features.

2. Run linter and [tests](./test)
   ```shell
   make fix tests
   ```

3. Test-build the package
   ```shell
   make clean build
   ```

4. Test-build the docs
   ```shell
   # Output entrypoint is docs/index.html
   make docs
   ```
   **Note**: Documentation output is not tracked in the repo

5. When you're happy with the work, raise a PR from your fork back into the nyx-sdk repo. 🎉
