"""PostToolUse hook (M3L3): react to Python syntax errors on our own.

Reads the hook payload (JSON on stdin), and if the edited/written file is a
.py, compiles it with py_compile. On a syntax error, prints the error to
stderr and exits 2 — for PostToolUse that is a blocking error whose stderr is
fed back to the agent, so it sees the mistake and fixes it immediately.

Non-.py files, missing paths, or clean compiles exit 0 (silent).
"""
import json
import py_compile
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # no/garbled payload — never block on hook plumbing

    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path.endswith(".py"):
        sys.exit(0)

    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        sys.stderr.write(f"py_compile: syntax error in {path}\n{exc.msg}\n")
        sys.exit(2)  # blocking error -> fed back to the agent to fix
    except FileNotFoundError:
        sys.exit(0)  # file gone (e.g. moved) — not our problem to block on


if __name__ == "__main__":
    main()
