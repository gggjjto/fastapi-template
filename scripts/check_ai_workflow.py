from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = [
    ROOT / ".claude",
    ROOT / ".codex",
    ROOT / "CLAUDE.md",
]

FORBIDDEN_REFERENCES = [
    ".claude/",
    ".codex/",
    ".Codex/",
    "CLAUDE.md",
]

REFERENCE_ALLOWLIST = {
    "docs/adr/0001-use-agents-as-ai-workflow-source.md",
    ".agents/requirements.md",
}

SKIP_REFERENCE_FILES = {
    "scripts/check_ai_workflow.py",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def check_forbidden_paths() -> list[str]:
    failures: list[str] = []
    for path in FORBIDDEN_PATHS:
        if path.exists():
            failures.append(f"Forbidden AI workflow path exists: {path.relative_to(ROOT)}")
    return failures


def check_forbidden_references() -> list[str]:
    failures: list[str] = []
    for file_name in tracked_files():
        if file_name in REFERENCE_ALLOWLIST or file_name in SKIP_REFERENCE_FILES:
            continue

        path = ROOT / file_name
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for pattern in FORBIDDEN_REFERENCES:
            if pattern in content:
                failures.append(f"{file_name}: contains forbidden reference {pattern!r}")
    return failures


def main() -> int:
    failures = check_forbidden_paths()
    failures.extend(check_forbidden_references())

    if failures:
        print("AI workflow guard failed. Use .agents as the single source of truth.")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AI workflow guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
