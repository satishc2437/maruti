#!/usr/bin/env python3
"""Mirror agents/<name>/ into .github/agents/ via relative symlinks.

The canonical authoring location for agent markdowns is agents/<name>/.
.github/agents/ is a per-repo publish target so this repo's own Copilot
can pick the agents up. Symlinking eliminates the drift risk of
hand-mirroring the two trees.

Modes:
    sync    Create or repair .github/agents/ symlinks to mirror agents/.
            Idempotent. Removes existing entries in .github/agents/ only
            if they are symlinks or text-fallback files (the Windows-no-
            symlink-support fallback). Refuses to overwrite real
            files/dirs unless --force is passed.
    check   Exit non-zero if any expected symlink is missing, broken, or
            points at the wrong target. Non-destructive.
    repair  Replace text-fallback files (left by a Windows clone without
            core.symlinks=true) with real symlinks. Convenience wrapper.

Discovery: every directory under agents/ that contains a
<dir-name>.agent.md becomes one mirror. If the agent dir also contains a
<dir-name>-internals/ subdirectory, that gets mirrored too. So an agent
named "agent-builder" produces two symlinks under .github/agents/:

    agent-builder.agent.md   -> ../../agents/agent-builder/agent-builder.agent.md
    agent-builder-internals  -> ../../agents/agent-builder/agent-builder-internals

Usage:
    python scripts/link_agents.py check
    python scripts/link_agents.py sync [--force]
    python scripts/link_agents.py repair
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / "agents"
PUBLISH_DIR = REPO_ROOT / ".github" / "agents"


@dataclass(frozen=True)
class Mirror:
    """One source-to-symlink pair (an agent.md or an internals/ directory)."""

    source: Path  # absolute path under agents/
    link: Path  # absolute path under .github/agents/
    relative_target: str  # POSIX-style relative path stored inside the symlink


def discover_mirrors() -> list[Mirror]:
    """Return one Mirror per agent.md (and per internals/) found under agents/."""
    if not AGENTS_DIR.is_dir():
        return []

    mirrors: list[Mirror] = []
    for agent_dir in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        name = agent_dir.name
        agent_md = agent_dir / f"{name}.agent.md"
        if not agent_md.is_file():
            continue
        mirrors.append(
            Mirror(
                source=agent_md,
                link=PUBLISH_DIR / f"{name}.agent.md",
                relative_target=f"../../agents/{name}/{name}.agent.md",
            )
        )
        internals = agent_dir / f"{name}-internals"
        if internals.is_dir():
            mirrors.append(
                Mirror(
                    source=internals,
                    link=PUBLISH_DIR / f"{name}-internals",
                    relative_target=f"../../agents/{name}/{name}-internals",
                )
            )
    return mirrors


def _is_real_symlink_to(link: Path, expected_target: str) -> bool:
    """Return True if link is an OS symlink pointing at expected_target."""
    if not link.is_symlink():
        return False
    actual = os.readlink(link).replace("\\", "/")
    return actual == expected_target


def _is_text_fallback(link: Path, expected_target: str) -> bool:
    """Return True if link is a real file whose content equals the target string.

    git on Windows without core.symlinks=true materializes a tracked
    symlink as a regular file whose body is the target path. We can
    repair these in-place.
    """
    if link.is_symlink() or not link.is_file():
        return False
    try:
        content = link.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return False
    return content == expected_target


def status_for(mirror: Mirror) -> str:
    """Classify a mirror's current state.

    Returns one of: ok, missing, wrong-target, text-fallback, real-file,
    real-dir.
    """
    link = mirror.link
    if not link.exists() and not link.is_symlink():
        return "missing"
    if _is_real_symlink_to(link, mirror.relative_target):
        return "ok"
    if link.is_symlink():
        # Either broken or pointing at the wrong target.
        return "wrong-target"
    if _is_text_fallback(link, mirror.relative_target):
        return "text-fallback"
    if link.is_dir():
        return "real-dir"
    return "real-file"


def _make_symlink(mirror: Mirror) -> None:
    """Create the symlink, requesting directory mode for internals/ targets."""
    os.symlink(
        mirror.relative_target,
        mirror.link,
        target_is_directory=mirror.source.is_dir(),
    )


def _emit_windows_hint(exc: OSError) -> None:
    """If we hit the Windows symlink-permission errno, print a remedy."""
    if sys.platform != "win32":
        return
    if "1314" not in str(exc):
        return
    print(
        "\nHint: on Windows, creating symlinks requires either Developer\n"
        "Mode (Settings > Privacy & security > For developers > Developer\n"
        "Mode) or admin rights. Also set `git config --global core.symlinks\n"
        "true` so symlinks survive clone/checkout.",
        file=sys.stderr,
    )


def cmd_check(mirrors: list[Mirror]) -> int:
    """Print a status report; exit 0 only if every mirror is OK."""
    bad = 0
    for mirror in mirrors:
        state = status_for(mirror)
        marker = "OK" if state == "ok" else state.upper()
        print(f"  [{marker}] {mirror.link.relative_to(REPO_ROOT)}")
        if state != "ok":
            bad += 1
    if bad:
        print(
            f"\n{bad} mirror(s) are not in the expected symlinked state. "
            "Run `python scripts/link_agents.py sync` (or `repair` if this "
            "is a fresh clone on Windows)."
        )
        return 1
    print(f"\nAll {len(mirrors)} agent mirror(s) are in sync.")
    return 0


def cmd_sync(mirrors: list[Mirror], *, force: bool) -> int:
    """Create/repair every mirror so it's a real symlink. Idempotent."""
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    untouched = 0
    for mirror in mirrors:
        state = status_for(mirror)
        if state == "ok":
            untouched += 1
            continue
        if state in ("missing", "wrong-target", "text-fallback"):
            if mirror.link.is_symlink() or mirror.link.is_file():
                mirror.link.unlink()
            try:
                _make_symlink(mirror)
            except OSError as exc:
                print(
                    f"  [FAIL] {mirror.link.relative_to(REPO_ROOT)}: {exc}",
                    file=sys.stderr,
                )
                _emit_windows_hint(exc)
                return 2
            print(f"  [LINK] {mirror.link.relative_to(REPO_ROOT)} -> {mirror.relative_target}")
            created += 1
        elif state in ("real-file", "real-dir"):
            if not force:
                print(
                    f"  [SKIP] {mirror.link.relative_to(REPO_ROOT)} is a real "
                    f"{state.split('-')[1]}; pass --force to overwrite.",
                    file=sys.stderr,
                )
                return 3
            if mirror.link.is_dir() and not mirror.link.is_symlink():
                shutil.rmtree(mirror.link)
            else:
                mirror.link.unlink()
            try:
                _make_symlink(mirror)
            except OSError as exc:
                print(
                    f"  [FAIL] {mirror.link.relative_to(REPO_ROOT)}: {exc}",
                    file=sys.stderr,
                )
                _emit_windows_hint(exc)
                return 2
            print(f"  [REPL] {mirror.link.relative_to(REPO_ROOT)} -> {mirror.relative_target}")
            created += 1
    print(f"\n{created} symlink(s) created/repaired, {untouched} already in sync.")
    return 0


def cmd_repair(mirrors: list[Mirror]) -> int:
    """Replace text-fallback files with real symlinks. Post-clone helper."""
    repaired = 0
    for mirror in mirrors:
        if status_for(mirror) != "text-fallback":
            continue
        mirror.link.unlink()
        try:
            _make_symlink(mirror)
        except OSError as exc:
            print(
                f"  [FAIL] {mirror.link.relative_to(REPO_ROOT)}: {exc}",
                file=sys.stderr,
            )
            _emit_windows_hint(exc)
            return 2
        print(f"  [LINK] {mirror.link.relative_to(REPO_ROOT)} -> {mirror.relative_target}")
        repaired += 1
    print(f"\n{repaired} text-fallback file(s) repaired.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the subcommand and dispatch."""
    parser = argparse.ArgumentParser(
        prog="link_agents",
        description="Mirror agents/<name>/ into .github/agents/ via symlinks.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="report symlink status; exit non-zero on drift")
    sync_parser = sub.add_parser("sync", help="create/repair the symlinks")
    sync_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite real files/dirs sitting at expected symlink locations",
    )
    sub.add_parser("repair", help="convert text-fallback files into real symlinks")
    args = parser.parse_args(argv)

    mirrors = discover_mirrors()
    if not mirrors:
        print("No agents discovered under agents/<name>/.", file=sys.stderr)
        return 1

    if args.cmd == "check":
        return cmd_check(mirrors)
    if args.cmd == "sync":
        return cmd_sync(mirrors, force=args.force)
    if args.cmd == "repair":
        return cmd_repair(mirrors)
    return 2


if __name__ == "__main__":
    sys.exit(main())
