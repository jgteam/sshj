from __future__ import annotations

import argparse
import os
import shlex
import sys
from dataclasses import dataclass
from typing import Literal, Sequence

from sshj.models import Bookmark
from sshj.ssh import connect, connect_tunnel
from sshj.storage import BookmarkStorage, KubeconfigStorage


@dataclass(slots=True)
class AliasMatch:
    bookmark: Bookmark
    mode: Literal["ssh", "tunnel"]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sshj",
        description="Manage and connect to SSH bookmarks.",
    )
    parser.add_argument(
        "alias",
        nargs="?",
        help="Connect to an SSH alias, or use 'kc' for kubeconfigs.",
    )
    parser.add_argument(
        "kc_name",
        nargs="?",
        help="Kubeconfig name when using 'kc'.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List saved bookmarks and exit.",
    )
    parser.add_argument("--emit-shell", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    storage = BookmarkStorage()

    if args.alias == "kc":
        if args.list or (args.emit_shell and not args.kc_name):
            print("Use 'sshj kc [name]' without --list.", file=sys.stderr)
            return 2
        return _kubeconfig_command(args.kc_name, args.emit_shell)

    if args.kc_name or args.emit_shell:
        print("A second name and --emit-shell are only valid with 'sshj kc'.", file=sys.stderr)
        return 2

    if args.alias and args.list:
        print("Use either an alias or --list, not both.", file=sys.stderr)
        return 2

    if args.alias:
        bookmarks = _load_bookmarks(storage)
        if bookmarks is None:
            return 1
        match = _find_by_alias(bookmarks, args.alias)
        if match is None:
            print(
                f"Alias '{args.alias}' not found. Open the app with 'sshj' to create it.",
                file=sys.stderr,
            )
            return 1
        if match.mode == "tunnel":
            connect_tunnel(match.bookmark)
        else:
            connect(match.bookmark)
        return 0

    if args.list:
        bookmarks = _load_bookmarks(storage)
        if bookmarks is None:
            return 1
        if not bookmarks:
            print("No bookmarks saved yet.")
            return 0

        for bookmark in bookmarks:
            print(_render_bookmark(bookmark))
        return 0

    from sshj.app import SSHJApp

    selected = SSHJApp(storage).run()
    if selected is not None:
        connect(selected)
    return 0


def _load_bookmarks(storage: BookmarkStorage) -> list[Bookmark] | None:
    try:
        return storage.load()
    except Exception as error:
        print(f"Failed to load bookmarks from {storage.path}: {error}", file=sys.stderr)
        return None


def _find_by_alias(bookmarks: list[Bookmark], alias: str) -> AliasMatch | None:
    for bookmark in bookmarks:
        if bookmark.alias == alias:
            mode: Literal["ssh", "tunnel"] = "tunnel" if bookmark.is_tunnel else "ssh"
            return AliasMatch(bookmark, mode)
        if bookmark.tunnel_alias == alias:
            return AliasMatch(bookmark, "tunnel")
    return None


def _render_bookmark(bookmark: Bookmark) -> str:
    alias = bookmark.alias or "(no alias)"
    port = f":{bookmark.port}" if bookmark.port else ""
    description = f" - {bookmark.description}" if bookmark.description else ""
    lines = [f"[SSH] {alias}: {bookmark.connection_target}{port}{description}"]
    if bookmark.has_tunnel:
        tunnel_alias = bookmark.tunnel_display_name or "(no tunnel alias)"
        lines.append(
            f"[TUN] {tunnel_alias}: {bookmark.tunnel_spec} via {bookmark.connection_target}{port}"
        )
    return "\n".join(lines)


def _kubeconfig_command(name: str | None, emit_shell: bool) -> int:
    storage = KubeconfigStorage()
    try:
        entries = storage.load()
    except Exception as error:
        print(f"Failed to load kubeconfigs from {storage.path}: {error}", file=sys.stderr)
        return 1

    selected = None
    if name is not None:
        selected = next((entry for entry in entries if entry.name.casefold() == name.casefold()), None)

    output = sys.stderr if emit_shell else sys.stdout
    if not entries:
        print("No kubeconfigs saved yet. Open 'sshj' to add one.", file=output)
    else:
        print("Available kubeconfigs (* = selected):", file=output)
        active_path = selected.expanded_path if selected else os.environ.get("KUBECONFIG")
        for entry in entries:
            marker = "*" if entry.expanded_path == active_path else " "
            print(f"{marker} {entry.name} -> {entry.expanded_path}", file=output)

    if selected is not None:
        print(f"export KUBECONFIG={shlex.quote(selected.expanded_path)}")
    return 1 if name is not None and selected is None else 0
