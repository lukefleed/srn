
import os
import sys
import argparse
import pathlib
import concurrent.futures
from functools import partial

from . import core
from . import utils
from . import gemini

DEFAULT_EXTENSIONS = "pdf"

def setup_arg_parser():
    """Configures and returns the argparse.ArgumentParser."""
    parser = argparse.ArgumentParser(
        description="Automatically rename files based on their content using Gemini.",
        usage="%(prog)s [options] FILE_OR_DIR [FILE_OR_DIR ...]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__ # Use the module docstring as the epilog
    )

    parser.add_argument(
        "input_paths",
        type=str,
        nargs='+',
        help="One or more paths to files or directories to process."
    )

    # Verbosity group
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose output (default)."
    )
    verbosity_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        default=False,
        help="Suppress all output except for errors."
    )

    parser.add_argument(
        "--no-thinking",
        action="store_true",
        default=False,
        help="Disable the 'thinking' feature for the model."
    )

    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=False,
        help="Enable recursive batch processing for directories or multiple files."
    )

    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        metavar="NUM",
        help="Number of parallel jobs (threads). Only used with -r. (Default: CPU count)"
    )

    parser.add_argument(
        "--ext",
        type=str,
        default=DEFAULT_EXTENSIONS,
        metavar="EXTENSIONS",
        help=f"Comma-separated file extensions to process (e.g., pdf,tex). Only used with -r. (Default: \"{DEFAULT_EXTENSIONS}\")"
    )

    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        default=False,
        help="Perform a dry run without renaming files.",
    )

    parser.add_argument(
        "-t", "--template",
        type=str,
        default=DEFAULT_TEMPLATE,
        help="Custom filename template (e.g., '{title}_{author}_{year}').",
    )

    parser.add_argument(
        "--context",
        type=str,
        help="Additional context to provide to the AI model.",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        metavar="NUM",
        help="Maximum number of pages to process for PDF files.",
    )

    parser.add_argument(
        "--on-conflict",
        type=str,
        default="skip",
        choices=["skip", "overwrite", "rename"],
        help="Action to take on filename conflict: skip (default), overwrite, or rename.",
    )

    return parser

def main():
    parser = setup_arg_parser()
    args = parser.parse_args()

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
