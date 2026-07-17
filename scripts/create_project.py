from __future__ import annotations

import argparse
import re
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EXCLUDES = {
    ".git",
    ".mypy_cache",
    ".omx",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage.xml",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    "*.egg-info",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".dockerignore",
    ".env",
    ".example",
    ".gitignore",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class ProjectNames:
    display_name: str
    package_name: str
    slug: str


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "new-project"


def package_name_from_slug(slug: str) -> str:
    package_name = slug.replace("-", "_")
    if package_name[0].isdigit():
        package_name = f"project_{package_name}"
    return package_name


def build_project_names(name: str) -> ProjectNames:
    slug = slugify(name)
    display_name = " ".join(part.capitalize() for part in slug.split("-"))
    return ProjectNames(
        display_name=display_name,
        package_name=package_name_from_slug(slug),
        slug=slug,
    )


def _matches_exclude(path: Path, patterns: Iterable[str]) -> bool:
    parts = set(path.parts)
    for pattern in patterns:
        if pattern in parts or path.match(pattern):
            return True
    return False


def should_copy(path: Path, excludes: Iterable[str] = DEFAULT_EXCLUDES) -> bool:
    relative = path.relative_to(ROOT)
    return not _matches_exclude(relative, excludes)


def is_text_file(path: Path) -> bool:
    if path.name in {".env.example", ".gitignore", ".dockerignore", "Dockerfile", "Makefile"}:
        return True
    return path.suffix in TEXT_SUFFIXES


def replacements(names: ProjectNames) -> dict[str, str]:
    return {
        "fastapi-template": names.slug,
        "Rapid Development Template": names.display_name,
        "FastAPI AI Template": names.display_name,
        (
            "A personal rapid-development template, starting with a production-minded FastAPI\n"
            "backend and designed to grow into a multi-project workspace when needed."
        ): f"{names.display_name} generated from the rapid development template.",
        "A compact FastAPI backend template optimized for AI-assisted development.": (
            f"{names.display_name} generated from the rapid development template."
        ),
    }


def rewrite_text(path: Path, names: ProjectNames) -> None:
    if not is_text_file(path):
        return

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return

    updated = content
    for old, new in replacements(names).items():
        updated = updated.replace(old, new)

    if updated != content:
        path.write_text(updated, encoding="utf-8")


def copy_template(target: Path, names: ProjectNames, *, force: bool = False) -> None:
    if target.exists():
        if not force:
            raise FileExistsError(f"Target already exists: {target}")
        if not target.is_dir():
            raise NotADirectoryError(f"Target exists and is not a directory: {target}")
    else:
        target.mkdir(parents=True)

    for source in ROOT.rglob("*"):
        if source == target or target in source.parents:
            continue
        if not should_copy(source):
            continue

        relative = source.relative_to(ROOT)
        destination = target / relative

        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        rewrite_text(destination, names)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create a project from this template.")
    parser.add_argument("name", help="New project name, for example my-saas-api.")
    parser.add_argument("target", type=Path, help="Directory to create or populate.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow copying into an existing directory.",
    )
    args = parser.parse_args(argv)

    names = build_project_names(args.name)
    target = args.target.expanduser().resolve()
    copy_template(target, names, force=args.force)

    print(f"Created {names.display_name} at {target}")
    print("Next steps:")
    print(f"  cd {target}")
    print("  make api-install")
    print("  cp apps/api/.env.example apps/api/.env")
    print("  make api-test-up && make api-ci")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
