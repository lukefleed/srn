#!/usr/bin/env python3

"""
srn: AI-Powered File Renamer

This script uses Google Gemini to intelligently rename files based on their content.
It is optimized for academic documents like papers, books, and notes but can be
applied to any text-based file.

USAGE:
    srn [OPTIONS] <FILE_OR_DIRECTORY>...

"""

from srn.cli import main

if __name__ == "__main__":
    main()