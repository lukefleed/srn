
# llmtitle: AI-Powered File Renamer

`llmtitle` is a command-line tool that uses Google Gemini to intelligently rename files based on their content. It is optimized for academic documents like papers, books, and notes but can be applied to any text-based file.

## Installation

This project uses `uv` for package management. To install the dependencies, run:

```bash
uv pip install -e .[test]
```

## Usage

```bash
llmtitle [OPTIONS] <FILE_OR_DIRECTORY>...
```

### Examples

1.  **Rename a single file:**

    ```bash
    llmtitle /path/to/document.pdf
    ```

2.  **Process multiple files recursively:**

    ```bash
    llmtitle -r file1.pdf "My Report.docx" notes.txt
    ```

3.  **Use a custom template for the new filename:**

    ```bash
    llmtitle -t "{first_author}_{year}_{title}" /path/to/papers/
    ```

4.  **Provide context to the AI:**

    ```bash
    llmtitle --context "These are all exam papers from the University of Bologna." /path/to/exams/
    ```

5.  **Perform a dry run to preview changes:**

    ```bash
    llmtitle -n /path/to/documents/
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
