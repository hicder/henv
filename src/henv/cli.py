from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HICDER_BIN = Path(".hicder") / "bin"
ENVRC_PATH = Path(".envrc")
ENVRC_PATH_ADD = "PATH_add .hicder/bin"
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="henv",
        description="Manage a local .hicder environment, similar to venv.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create .hicder/bin and set up direnv if available")

    bin_parser = subparsers.add_parser(
        "bin",
        help="Create a symlink under .hicder/bin",
    )
    bin_parser.add_argument("name", help="Name of the symlink (e.g. clang)")
    bin_parser.add_argument("target", help="Path to the real binary")

    env_parser = subparsers.add_parser(
        "env",
        help="Append or update an export in .envrc",
    )
    env_parser.add_argument("name", help="Variable name (e.g. FOO)")
    env_parser.add_argument(
        "value",
        nargs=argparse.REMAINDER,
        help="Variable value (e.g. bar). May start with -.",
    )

    unenv_parser = subparsers.add_parser(
        "unenv",
        help="Remove an export from .envrc",
    )
    unenv_parser.add_argument("name", help="Variable name (e.g. FOO)")

    args = parser.parse_args(argv)

    if args.command == "init":
        return cmd_init()
    if args.command == "bin":
        return cmd_bin(args.name, args.target)
    if args.command == "env":
        value_parts = list(args.value)
        if value_parts[:1] == ["--"]:
            value_parts = value_parts[1:]
        if not value_parts:
            env_parser.error("the following arguments are required: value")
        return cmd_env(args.name, " ".join(value_parts))
    if args.command == "unenv":
        return cmd_unenv(args.name)
    parser.error(f"unknown command: {args.command}")
    return 2


def cmd_init() -> int:
    bin_dir = Path.cwd() / HICDER_BIN
    created = not bin_dir.exists()
    bin_dir.mkdir(parents=True, exist_ok=True)
    print(f"created {bin_dir}" if created else f"exists {bin_dir}")

    direnv = shutil.which("direnv")
    if direnv is None:
        print("direnv not found; skipped .envrc")
        return 0

    ensure_envrc(Path.cwd() / ENVRC_PATH)
    return direnv_allow()


def cmd_bin(name: str, target: str) -> int:
    if not name or name in {".", ".."} or "/" in name or os.sep in name:
        print(f"invalid symlink name: {name}", file=sys.stderr)
        return 1

    target_path = Path(target).expanduser()
    if not target_path.is_absolute():
        target_path = (Path.cwd() / target_path).resolve()

    if not target_path.exists():
        print(f"target does not exist: {target_path}", file=sys.stderr)
        return 1

    bin_dir = Path.cwd() / HICDER_BIN
    bin_dir.mkdir(parents=True, exist_ok=True)
    link_path = bin_dir / name

    if link_path.exists() or link_path.is_symlink():
        if link_path.is_symlink():
            link_path.unlink()
        else:
            print(f"refusing to replace non-symlink: {link_path}", file=sys.stderr)
            return 1

    link_path.symlink_to(target_path)
    print(f"{link_path} -> {target_path}")
    return 0


def cmd_env(name: str, value: str) -> int:
    if not ENV_NAME_RE.match(name):
        print(f"invalid variable name: {name}", file=sys.stderr)
        return 1

    envrc = Path.cwd() / ENVRC_PATH
    new_line = f"export {name}={value}"
    prefix = f"export {name}="

    if not envrc.exists():
        envrc.write_text(f"{new_line}\n")
        print(f"created {envrc}")
        return direnv_allow()

    lines = envrc.read_text().splitlines()
    found = False
    changed = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip().startswith(prefix):
            if not found:
                new_lines.append(new_line)
                found = True
                changed = line.strip() != new_line
            else:
                changed = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(new_line)
        changed = True

    if not changed:
        print(f"exists {envrc}")
        return 0

    envrc.write_text("\n".join(new_lines) + "\n")
    print(f"updated {envrc}")
    return direnv_allow()


def cmd_unenv(name: str) -> int:
    if not ENV_NAME_RE.match(name):
        print(f"invalid variable name: {name}", file=sys.stderr)
        return 1

    envrc = Path.cwd() / ENVRC_PATH
    if not envrc.exists():
        print(f"missing {envrc}")
        return 0

    prefix = f"export {name}="
    lines = envrc.read_text().splitlines()
    new_lines = [line for line in lines if not line.strip().startswith(prefix)]
    if len(new_lines) == len(lines):
        print(f"missing {name} in {envrc}")
        return 0

    envrc.write_text("\n".join(new_lines) + "\n" if new_lines else "")
    print(f"updated {envrc}")
    return direnv_allow()


def direnv_allow() -> int:
    direnv = shutil.which("direnv")
    if direnv is None:
        print("direnv not found; skipped direnv allow")
        return 0

    result = subprocess.run([direnv, "allow"], cwd=Path.cwd())
    if result.returncode != 0:
        print("direnv allow failed", file=sys.stderr)
        return result.returncode
    print("direnv allow")
    return 0


def ensure_envrc(envrc: Path) -> None:
    if not envrc.exists():
        envrc.write_text(f"{ENVRC_PATH_ADD}\n")
        print(f"created {envrc}")
        return

    text = envrc.read_text()
    first_line = text.splitlines()[0].strip() if text.strip() else ""
    if first_line == ENVRC_PATH_ADD:
        print(f"exists {envrc}")
        return

    envrc.write_text(f"{ENVRC_PATH_ADD}\n{text}" if text else f"{ENVRC_PATH_ADD}\n")
    print(f"updated {envrc}")

