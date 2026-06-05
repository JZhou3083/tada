# Contributing

This guide is intended for developers contributing to Tableau Metadata Agent.

## Set up your environment

Create and activate a virtual environment, then install dependencies.

Using `uv`:

```shell
uv sync
```

Using `pip`:

```shell
pip install .
```

## Install the CLI locally

Install the package in editable mode:

```shell
uv run pip install -e .
```

Or, using `pip`:

```shell
pip install -e .
```

This makes the following commands available on your `PATH`:

- `tada`
- `tada-trace-viewer`

Alternatively, you can run the primary CLI app directly:

```shell
python tada-cli.py
```

## Environment variables

Copy the variables from the committed `.env.example` file into a local `.env` file:

```shell
cp .env.example .env
```

Update the values in `.env` for your local development environment.

The `.env` file should remain gitignored and must not be committed.

## Pre-commit hooks

Install the required Git hooks, including commit message checks:

```shell
uv run pre-commit install
```

If you are not using `uv`, activate your virtual environment and run:

```shell
pre-commit install
```

> **Note**
> The first time pre-commit runs, it may take a few minutes to set up hook environments.
> This only happens once; subsequent runs are faster.

The pre-commit hooks enforce:

- Code quality checks
- Formatting standards
- Commit message standards

## Commit messages

This project follows the conventional commit style to keep history readable and support semantic versioning.

Commit message enforcement is handled by `commitlint`.

`commitizen` is also included to help write compliant commit messages.

> **Note**
> Commitizen is recommended but not required.
> All valid conventional commits, including types not prompted by Commitizen such as `chore` and `revert`, are accepted if they pass commitlint.

## Writing commits with Commitizen

Using `uv`:

```shell
uv run cz commit
```

Short form:

```shell
uv run cz c
```

Without `uv`, with your virtual environment activated:

```shell
cz commit
```

This acts as a guided replacement for `git commit`.

## Run checks before committing

To avoid writing a commit message only for the commit to be rejected by another hook, run the pre-commit checks first:

```shell
uv run pre-commit run
```

To run checks against all files:

```shell
uv run pre-commit run --all-files
```
