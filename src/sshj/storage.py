from __future__ import annotations

import json
import os
from pathlib import Path

from sshj.models import Bookmark
from sshj.kubeconfig import KubeconfigEntry

DEFAULT_BOOKMARK_PATH = Path.home() / ".sshj" / "bookmarks.json"
DEFAULT_KUBECONFIG_PATH = Path.home() / ".sshj" / "kubeconfigs.json"


class BookmarkStorage:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.environ.get("SSHJ_BOOKMARKS")
        if path is not None:
            self.path = path.expanduser()
        elif env_path:
            self.path = Path(env_path).expanduser()
        else:
            self.path = DEFAULT_BOOKMARK_PATH

    def load(self) -> list[Bookmark]:
        if not self.path.exists():
            return []

        raw_data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError(f"Bookmark file must contain a list: {self.path}")

        bookmarks: list[Bookmark] = []
        for entry in raw_data:
            if not isinstance(entry, dict):
                continue
            try:
                bookmarks.append(Bookmark.from_dict(entry))
            except (TypeError, ValueError):
                continue
        return bookmarks

    def save(self, bookmarks: list[Bookmark]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = [bookmark.to_dict() for bookmark in bookmarks]
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)


class KubeconfigStorage:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.environ.get("SSHJ_KUBECONFIGS")
        if path is not None:
            self.path = path.expanduser()
        elif env_path:
            self.path = Path(env_path).expanduser()
        else:
            self.path = DEFAULT_KUBECONFIG_PATH

    def load(self) -> list[KubeconfigEntry]:
        if not self.path.exists():
            return []
        raw_data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError(f"Kubeconfig file must contain a list: {self.path}")
        entries: list[KubeconfigEntry] = []
        for entry in raw_data:
            if not isinstance(entry, dict):
                continue
            try:
                entries.append(KubeconfigEntry.from_dict(entry))
            except (TypeError, ValueError):
                continue
        return entries

    def save(self, entries: list[KubeconfigEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps([entry.to_dict() for entry in entries], indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.path)
