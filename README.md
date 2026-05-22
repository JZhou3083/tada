# Tableau Metadata Agent

An LLM-driven CLI tool for generating standardized Tableau workbook documentation.

## Getting started (developers)

> **Note**
> These instructions are intended for developers. External users are expected to install the package via Artifact Registry.

### Set up your environment

Create and activate a virtual environment, then install dependencies:

- **uv users**
    ```shell
    uv sync
    ```
- **pip users**
    ```shell
    pip install .
    ```

### Install the CLI (recommended)

Install the package in editable mode:

```shell
uv run pip install -e .
# or
pip install -e .
```

This makes the `tada` & `tada-trace-viewer` commands available on your PATH.

Alternatively, you can run the primary `tada` CLI app directly:

```shell
python tada-cli.py
```

### Setup your environment variables

Copy the variables from the git-committed `.env.example` file to your local gitignored `.env` file, setting the values appropriately for your local development preferences.


## CLI capabilities

The CLI currently supports:

*   ✅ **Generating standardized Tableau workbook documentation**
*   ✅ **Viewing the traces of previous runs in a local Arize Phoenix server**


## Usage

To launch the documentation workflow:

```shell
tada document
# or, to select via the interactive fallback menu
tada
```

You *can* specify the application arguments for your run via command-line flags (for example if automating usage of the tool). See one example below:

```shell
tada document --workbook my_workbook.twb --output documentation.md --all-sections
```

To view available commands and options:

```shell
tada --help / tada document --help
```

Most users will find it more convenient to not provide flags, in which case the app will fall back to prompting the user for missing application arguments via interactive command-line prompts.

### Observability

All runs will generate log and OTEL trace artifacts.
For more visibility of these artifacts enable debug mode:

```shell
tada --debug
tada --debug document
```

Debug mode will print logs to the console for the user to view and will alert you of the location of your run artifacts (this defaults to the user's OS' app state directory but can be set via the `TADA_STATE_DIR` environment variable).

After traces have been generated users can run the trace viewer command:

```shell
tada-trace-viewer
```

This command requires some additional dependencies which can be installed as follows:

```shell
uv sync --extra trace-viewer
# or
pip install '.[trace-viewer]'
```

The trace viewer command will load in any traces which have been previously generated (at command runtime) and launch a local Arize Phoenix server where the details of those traces can be viewed (such as retries, evaluations, intermediary LLM generations, etc.).

## Contributing

### Pre-commit hooks

Install all required Git hooks (including commit message checks):

```shell
uv run pre-commit install
```

If you're not using uv, activate your virtual environment and run:

```shell
pre-commit install
```

> **Note**
> The first time pre-commit runs, it may take a few minutes to set up hook environments.
> This only happens once; subsequent runs are fast.
>
> The pre-commit hooks enforce code quality checks and commit message standards.

### Commit messages

We follow a **conventional commit style** to keep history readable and support semantic versioning.

- Commit enforcement is handled by **commitlint** in the background
- **commitizen** is included to make writing compliant commit messages easier

> **Note**
> Commitizen is recommended but not required.
> All valid conventional commits (including types not prompted by commitizen, such as `chore` and `revert`) are still accepted and enforced by commitlint.

#### Writing commits with commitizen (recommended)

Using uv:

```shell
uv run cz commit
# Short form
uv run cz c
```

Without uv (virtual environment activated):

```shell
cz commit
```

This acts as a drop-in replacement for `git commit` and guides you through creating a valid message.

##### Tip: run checks before committing

To avoid writing a full commit message via commitizen only for the commit to be rejected by a different hook, you can run all pre-commit checks manually first:

```shell
uv run pre-commit run
```
