from __future__ import annotations

import os
from pathlib import Path

from sshj.models import Bookmark


def build_ssh_command(bookmark: Bookmark) -> list[str]:
    if bookmark.is_tunnel:
        return build_tunnel_command(bookmark)

    command = ["ssh"]
    _add_common_options(command, bookmark)
    command.append(bookmark.connection_target)
    return command


def build_tunnel_command(bookmark: Bookmark) -> list[str]:
    tunnel_spec = bookmark.tunnel_spec
    if tunnel_spec is None:
        raise ValueError("Tunnel entries require local and remote forwarding fields.")

    command = ["ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-L", tunnel_spec]
    _add_common_options(command, bookmark)
    command.append(bookmark.connection_target)
    return command


def _add_common_options(command: list[str], bookmark: Bookmark) -> None:
    if bookmark.port:
        command.extend(["-p", str(bookmark.port)])

    if bookmark.key_path:
        expanded_key = str(Path(bookmark.key_path).expanduser())
        command.extend(["-i", expanded_key])


def connect(bookmark: Bookmark) -> None:
    command = build_ssh_command(bookmark)
    os.execvp(command[0], command)
