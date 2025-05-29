#!/usr/bin/env python3
# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Check for proper copyright headers in Python files."""

import sys
from pathlib import Path

EXPECTED_HEADER = "# Copyright 2025 Fact Fiber Inc. All rights reserved."


MIN_ARGS = 2


def check_copyright_header(file_path: Path) -> bool:
    """Check if file has the correct copyright header."""
    try:
        with file_path.open(encoding="utf-8") as f:
            first_line = f.readline().strip()
            # If first line is shebang, check second line
            if first_line.startswith("#!"):
                second_line = f.readline().strip()
                return second_line == EXPECTED_HEADER
            return first_line == EXPECTED_HEADER
    except (OSError, ValueError):
        return False


def main() -> int:
    """Main function to check copyright headers."""
    if len(sys.argv) < MIN_ARGS:
        print(  # noqa: T201
            "Usage: python check_copyright.py <file1> [file2] ..."
        )
        return 1

    exit_code = 0
    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not check_copyright_header(path):
            print(  # noqa: T201
                f"Missing or incorrect copyright header: {file_path}"
            )
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
