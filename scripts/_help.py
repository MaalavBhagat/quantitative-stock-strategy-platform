"""`--help` / `-h` for the project scripts (Phase 10, Step 10.5): print what the script does and how to run it, then
exit WITHOUT doing anything (no download, no run, no file written).

Called first inside each script's `if __name__ == "__main__":` block (scripts that use argparse have their own).
"""

import sys


def handle_help(doc: str | None) -> None:
    """If -h / --help was given: print the docstring's first paragraph as ONE line + its 'Run:' line(s), exit 0."""
    if not {"-h", "--help"} & set(sys.argv[1:]):
        return
    text = (doc or "").strip()
    first = " ".join(text.split("\n\n")[0].split()) if text else "(no description)"
    print(first)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("Run ", "Run:", "Run (", "uv run")):
            print("  " + stripped)
    sys.exit(0)
