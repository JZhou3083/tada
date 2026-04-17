# Tableau Metadata Agent

An LLM-driven CLI tool for working with Tableau workbooks, with a focus on generating standardized documentation.

## Getting started (developers)

> **Note**  
> These instructions are intended for developers. External users are expected to install the package via Artifact Registry.

### Set up your environment

Create and activate a virtual environment, then install dependencies:

- **uv users**
    ```bash
    uv sync
    ```
- **pip users**
    ```bash
    pip install .
    ```

### Install the CLI (recommended)

Install the package in editable mode:

```bash
uv run pip install -e .
# or
pip install -e .
```

This makes the `tada` command available on your PATH.

Alternatively, you can run the CLI directly:

```bash
python tada-cli.py
```

## CLI capabilities

The CLI currently supports:

*   ✅ **Generate standardized Tableau workbook documentation**
*   🚧 **Compare two workbooks** (work in progress)
*   🚧 **Q\&A chat for a single workbook** (work in progress)

## Usage

For available commands and options:

```bash
tada --help
```
