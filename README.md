# Tableau Metadata Agent

An LLM-driven CLI tool for generating standardised Tableau workbook documentation.

## Overview

Tableau Metadata Agent provides a CLI for documenting Tableau workbooks in a consistent format.

The CLI currently supports:

- ✅ Generating standardised Tableau workbook documentation
- ✅ Viewing traces from previous runs in a local Arize Phoenix server

## Installation

External users are expected to install the package via Artifact Registry.

For local development setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Usage

To launch the documentation workflow:

```shell
tada document
```

Or launch the interactive fallback menu:

```shell
tada
```

You can also provide arguments via command-line flags, which is useful for automation:

```shell
tada document --workbook my_workbook.twb --output documentation.md --all-sections
```

To view available commands and options:

```shell
tada --help
tada document --help
```

If required arguments are not provided, the CLI will prompt for them interactively.

## Observability

All runs generate log and OpenTelemetry trace artifacts.

To enable debug mode:

```shell
tada --debug
tada --debug document
```

Debug mode prints logs to the console and shows the location of run artifacts.

By default, artifacts are stored in the operating system's application state directory. This location can be overridden by setting the `TADA_STATE_DIR` environment variable.

## Trace viewer

After traces have been generated, you can launch the trace viewer:

```shell
tada-trace-viewer
```

This loads previously generated traces and starts a local Arize Phoenix server, where you can inspect details such as:

- Retries
- Evaluations
- Intermediate LLM generations
- Trace metadata

The trace viewer requires additional dependencies:

```shell
uv sync --extra trace-viewer
```

Or, using pip:

```shell
pip install '.[trace-viewer]'
```
