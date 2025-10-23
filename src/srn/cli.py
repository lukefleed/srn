
import os
import sys
import argparse
import pathlib
import concurrent.futures
from functools import partial

from . import core
from . import utils
from . import gemini
from . import credentials

DEFAULT_EXTENSIONS = "pdf,doc,docx,txt,ppt,pptx,xls,xlsx"

def setup_arg_parser():
    """Configures and returns the argparse.ArgumentParser."""
    parser = argparse.ArgumentParser(
        description="""srn: An intelligent file renamer powered by Gemini.

This tool analyzes the content of your files (currently PDFs) and suggests
more descriptive and organized filenames, leveraging the power of Google Gemini's
large language models. Ideal for organizing academic documents, research papers,
or any collection of files that needs consistent and meaningful naming.""",
        usage="%(prog)s [OPTIONS] [FILE_OR_DIRECTORY ...]",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:
  srn --api-key
    Prompts to enter your Gemini API key and saves it securely.

  srn my_document.pdf
    Renames a single PDF file based on its content.

  srn -r ~/Documents/Research/
    Recursively processes all PDF files in a directory and its subdirectories.

  srn -r --ext pdf,tex ~/Projects/
    Recursively processes PDF and TeX files in a directory.

  srn -n my_report.pdf
    Performs a "dry run" to see suggested names without actually renaming files.

  srn -t "{title} - {author} ({year})" article.pdf
    Renames a file using a custom template. Available fields depend on the file
    content and the model's ability to extract them. If omitted, the model will
    try to deduce the best name.

  srn --model gemini-2.5-flash-lite -r ~/Downloads/
    Uses a specific Gemini model to process files in a directory.

  srn --on-conflict overwrite old_file.pdf
    Overwrites an existing file in case of a name conflict.

  srn --context "This is a quantum physics document." paper.pdf
    Provides additional context to the AI model to improve the relevance of the
    suggested filename.

For more details, visit the project documentation.
"""
    )

    parser.add_argument(
        "--api-key",
        action="store_true",
        help="""Prompts for the Gemini API key and saves it securely for future use.
The key is stored in ~/.srn/.env with restricted permissions.""",
    )

    parser.add_argument(
        "input_paths",
        type=str,
        nargs='*',
        help="""One or more paths to files or directories to process.
If directories are specified, the -r (recursive) option is recommended.""",
    )

    # Verbosity group
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose output (default).",
    )
    verbosity_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        default=False,
        help="Suppress all output except for errors.",
    )

    parser.add_argument(
        "--no-thinking",
        action="store_true",
        default=False,
        help="""Disables the AI model's "thinking" phase, potentially speeding up
the process but possibly reducing the quality of suggested names.""",
    )

    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=False,
        help="""Enables recursive batch processing for directories or multiple files.
When used with directories, it searches for files specified by --ext.""",
    )

    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        metavar="NUM",
        help="""Number of parallel jobs (threads) to use.
Only used with the -r option. (Default: CPU core count).""",
    )

    parser.add_argument(
        "--ext",
        type=str,
        default=DEFAULT_EXTENSIONS,
        metavar="EXTENSIONS",
        help=f"""Comma-separated file extensions to process (e.g., pdf,doc,txt).
Only used with the -r option. (Default: "{DEFAULT_EXTENSIONS}")."""
    )

    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        default=False,
        help="""Performs a simulation without actually renaming files,
only showing the suggested names.""",
    )

    parser.add_argument(
        "-t", "--template",
        type=str,
        help="""Custom filename template (e.g., '{title}_{author}_{year}').
Available fields depend on the file content and the model's ability to extract
such information. If omitted, the model will try to deduce the best name.""",
    )

    parser.add_argument(
        "--context",
        type=str,
        help="""Additional context to provide to the AI model to help it
generate more relevant filenames.""",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        metavar="NUM",
        help="""Maximum number of pages to process for PDF files.
Useful for very large files to limit token consumption.""",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=gemini.DEFAULT_MODEL,
        choices=gemini.ALLOWED_MODELS,
        help=f"""Specify the Gemini model to use.
(Default: {gemini.DEFAULT_MODEL}).
Available models: {', '.join(gemini.ALLOWED_MODELS)}.""",
    )

    parser.add_argument(
        "--on-conflict",
        type=str,
        default="skip",
        choices=["skip", "overwrite", "rename"],
        help="""Action to take on filename conflict:
  skip: skips the file (default).
  overwrite: overwrites the existing file.
  rename: adds a numeric suffix to avoid conflicts.""",
    )

    return parser

def main():
    parser = setup_arg_parser()
    args = parser.parse_args()

    if args.api_key:
        credentials.prompt_for_api_key()
        sys.exit(0)
        return # Ensure the function exits

    # Manual validation for input_paths if --api-key is not used
    if not args.api_key and not args.input_paths:
        parser.error("The following arguments are required: input_paths")

    # --- Argument Validation ---
    if not args.recursive:
        if len(args.input_paths) > 1:
            parser.error("Multiple paths provided without the -r flag. Use -r to process a batch.")

        path = pathlib.Path(args.input_paths[0])
        if path.is_dir():
            parser.error("Cannot process a directory without the -r flag. Use -r to scan recursively.")
        if not path.exists():
            parser.error(f"File not found: {path}")
        if not path.is_file():
            parser.error(f"Input path is not a file: {path}")

        # Non-recursive options check
        if args.jobs is not None:
            print("Warning: -j/--jobs flag has no effect without -r.", file=sys.stderr)
        if args.ext != DEFAULT_EXTENSIONS:
            parser.error("--ext can only be used with the -r flag.")

        files_to_process = [path]
        num_workers = 1

    else:
        # Recursive / Batch mode
        files_to_process = utils.discover_files(args.input_paths, args.ext)
        if not files_to_process:
            print("No files found matching the criteria.")
            sys.exit(0)

        num_workers = args.jobs if args.jobs is not None and args.jobs > 0 else os.cpu_count()
        if num_workers is None:
            num_workers = 4 # Fallback if os.cpu_count() fails

        # Use the smaller of desired workers or number of files
        # Do not spawn more threads than there are files to process.
        desired_workers = args.jobs if args.jobs is not None and args.jobs > 0 else os.cpu_count()
        if desired_workers is None:
            desired_workers = 4 # Fallback if os.cpu_count() fails

        num_workers = min(desired_workers, len(files_to_process))

    # --- Setup Worker Function ---
    token_counter = utils.ThreadSafeCounter()
    worker_func = partial(
        core.process_and_rename_file,
        model_name=args.model,
        disable_thinking=args.no_thinking,
        dry_run=args.dry_run,
        on_conflict=args.on_conflict,
        template=args.template,
        context=args.context,
        max_pages=args.max_pages,
        token_counter=token_counter
    )

    # --- Execution ---
    if args.dry_run:
        print(f"{utils.TerminalColors.BOLD}--- DRY RUN MODE ---{utils.TerminalColors.ENDC}")

    if not args.quiet:
        print(f"Found {len(files_to_process)} file(s). Processing with {num_workers} worker(s)...")

    success_count = 0
    skipped_count = 0
    error_count = 0
    dry_run_count = 0
    conflict_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        try:
            results = list(executor.map(worker_func, files_to_process))
        except KeyboardInterrupt:
            print(f"\n{utils.TerminalColors.RED}Caught Interrupt. Shutting down workers...{utils.TerminalColors.ENDC}", file=sys.stderr)
            executor.shutdown(wait=False, cancel_futures=True)
            sys.exit(1)

    if not args.quiet:
        print(f"\n{utils.TerminalColors.BOLD}--- Processing Complete ---{utils.TerminalColors.ENDC}")
        for original, new, status in results:
            if status == "success":
                print(f"{utils.TerminalColors.GREEN}[OK] Renamed:{utils.TerminalColors.ENDC}\n     {original.name}\n  -> {new.name}")
                success_count += 1
            elif status == "dry_run_success":
                print(f"{utils.TerminalColors.GREEN}[DRY-RUN] Would rename:{utils.TerminalColors.ENDC}\n     {original.name}\n  -> {new.name}")
                dry_run_count += 1
            elif status == "skipped":
                print(f"{utils.TerminalColors.YELLOW}[SKIP] Name already correct: {original.name}{utils.TerminalColors.ENDC}")
                skipped_count += 1
            elif status == "conflict_skipped":
                print(f"{utils.TerminalColors.YELLOW}[SKIP] Conflict: {new.name} already exists.{utils.TerminalColors.ENDC}")
                conflict_count += 1
            else:
                print(f"{utils.TerminalColors.RED}[FAIL] {original.name}\n     Error: {status}{utils.TerminalColors.ENDC}", file=sys.stderr)
                error_count += 1

    print(f"\n{utils.TerminalColors.BOLD}--- Summary ---{utils.TerminalColors.ENDC}")
    if args.dry_run:
        print(f"{utils.TerminalColors.GREEN}Would rename: {dry_run_count}{utils.TerminalColors.ENDC}")
    else:
        print(f"{utils.TerminalColors.GREEN}Successful: {success_count}{utils.TerminalColors.ENDC}")
    print(f"{utils.TerminalColors.YELLOW}Skipped:    {skipped_count}{utils.TerminalColors.ENDC}")
    print(f"{utils.TerminalColors.YELLOW}Conflicts:  {conflict_count}{utils.TerminalColors.ENDC}")
    if error_count > 0:
        print(f"{utils.TerminalColors.RED}Failed:     {error_count}{utils.TerminalColors.ENDC}")
    else:
        print(f"Failed:     {error_count}")
    
    print(f"Total tokens used: {token_counter.value}")

    if error_count > 0:
        sys.exit(1)
