from __future__ import annotations

import os
from pathlib import Path

from sshj.models import Bookmark


def build_ssh_command(bookmark: Bookmark) -> list[str]:
    command = ["ssh"]

    if bookmark.port:
        command.extend(["-p", str(bookmark.port)])

    if bookmark.key_path:
        expanded_key = str(Path(bookmark.key_path).expanduser())
        command.extend(["-i", expanded_key])

    command.append(bookmark.connection_target)
    return command


def connect(bookmark: Bookmark) -> None:
    command = build_ssh_command(bookmark)
    os.execvp(command[0], command)
