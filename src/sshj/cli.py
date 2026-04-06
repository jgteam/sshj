from __future__ import annotations

import argparse
import sys
from typing import Sequence

from sshj.models import Bookmark
from sshj.ssh import connect
from sshj.storage import BookmarkStorage


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sshj",
        description="Manage and connect to SSH bookmarks.",
    )
    parser.add_argument(
        "alias",
        nargs="?",
        help="Connect directly to a saved bookmark alias.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List saved bookmarks and exit.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    storage = BookmarkStorage()

    if args.alias and args.list:
        print("Use either an alias or --list, not both.", file=sys.stderr)
        return 2

    if args.alias:
        bookmarks = _load_bookmarks(storage)
        if bookmarks is None:
            return 1
        bookmark = _find_by_alias(bookmarks, args.alias)
        if bookmark is None:
            print(
                f"Alias '{args.alias}' not found. Open the app with 'sshj' to create it.",
                file=sys.stderr,
            )
            return 1
        connect(bookmark)
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


def _find_by_alias(bookmarks: list[Bookmark], alias: str) -> Bookmark | None:
    for bookmark in bookmarks:
        if bookmark.alias == alias:
            return bookmark
    return None


def _render_bookmark(bookmark: Bookmark) -> str:
    alias = bookmark.alias or "(no alias)"
    port = f":{bookmark.port}" if bookmark.port else ""
    description = f" - {bookmark.description}" if bookmark.description else ""
    return f"{alias}: {bookmark.connection_target}{port}{description}"
