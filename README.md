# Tableau Metadata Agent

An LLM-driven CLI tool for working with Tableau workbooks, with a focus on generating standardized documentation.

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

This makes the `tada` command available on your PATH.

Alternatively, you can run the CLI directly:

```shell
python tada-cli.py
```

## CLI capabilities

The CLI currently supports:

*   ✅ **Generate standardized Tableau workbook documentation**
*   🚧 **Compare two workbooks** (work in progress)
*   🚧 **Q\&A chat for a single workbook** (work in progress)

## Usage

For available commands and options:

```shell
tada --help
```

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
