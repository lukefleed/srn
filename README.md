
# srn: AI-Powered File Renamer

`srn` is a command-line tool that uses Google Gemini to intelligently rename files based on their content. It is optimized for academic documents like papers, books, and notes but can be applied to any text-based file.

## Installation

This project uses `uv` for package management.

### For Development

To set up the project for development (including running tests), install dependencies in editable mode:

```bash
uv pip install -e .[test]
```

### For Production/Global Use

To package and install `srn` for global use on your system:

1.  **Build the package:**
    ```bash
    uv build
    ```
    This will create a distributable wheel file (e.g., `dist/srn-0.1.0-py3-none-any.whl`).

2.  **Install the package:**
    ```bash
    uv pip install dist/*.whl
    ```
    This installs `srn` into your `uv` virtual environment.

3.  **Make `srn` globally accessible (optional):**
    To run `srn` from any directory without `uv run`, add your virtual environment's `bin` directory to your system's PATH.
    Assuming your virtual environment is `.venv` in the project root, add the following line to your shell's configuration file (e.g., `~/.bashrc` or `~/.zshrc`):

    ```bash
    export PATH="/path/to/your/project/.venv/bin:$PATH"
    ```
    After saving, open a new terminal or run `source ~/.bashrc` (or `source ~/.zshrc`).

## Usage

You can run `srn` in two ways:

1.  **Within the `uv` environment (recommended):**
    ```bash
    uv run srn [OPTIONS] <FILE_OR_DIRECTORY>...
    ```
2.  **Globally (after adding to PATH):**
    ```bash
    srn [OPTIONS] <FILE_OR_DIRECTORY>...
    ```

### Examples

1.  **Rename a single file:**

    ```bash
    uv run srn /path/to/document.pdf
    ```

2.  **Process multiple files recursively:**

    ```bash
    uv run srn -r file1.pdf "My Report.docx" notes.txt
    ```

3.  **Use a custom template for the new filename:**

    ```bash
    uv run srn -t "{first_author}_{year}_{title}" /path/to/papers/
    ```

4.  **Provide context to the AI:**

    ```bash
    uv run srn --context "These are all exam papers from the University of Bologna." /path/to/exams/
    ```

5.  **Perform a dry run to preview changes:**

    ```bash
    uv run srn -n /path/to/documents/
    ```

### Options

-   `-m, --model`: Specify the Gemini model to use.
-   `-r, --recursive`: Enable batch processing for multiple files or directories.
-   `-j, --jobs`: Number of parallel jobs for batch processing.
-   `--ext`: Comma-separated list of file extensions to process.
-   `-n, --dry-run`: Perform a dry run without renaming files.
-   `-t, --template`: Custom filename template.
-   `--context`: Additional context to provide to the AI model.
-   `--on-conflict`: Action to take on filename conflict (`skip`, `overwrite`, `rename`).
-   `--max-pages`: Maximum number of pages to process for PDF files.
