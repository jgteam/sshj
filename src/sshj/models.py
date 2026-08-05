from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Bookmark:
    host: str
    username: str | None = None
    port: int | None = None
    key_path: str | None = None
    alias: str | None = None
    description: str | None = None
    entry_type: str = "ssh"
    tunnel_alias: str | None = None
    local_bind_host: str | None = None
    local_port: int | None = None
    remote_host: str | None = None
    remote_port: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        host = str(data.get("host", "")).strip()
        username = _optional_text(data.get("username"))
        key_path = _optional_text(data.get("key_path"))
        alias = _optional_text(data.get("alias"))
        description = _optional_text(data.get("description"))
        entry_type = _optional_text(data.get("entry_type")) or "ssh"
        tunnel_alias = _optional_text(data.get("tunnel_alias"))
        if entry_type == "tunnel" and tunnel_alias is None:
            tunnel_alias = alias
            alias = None

        if not host:
            raise ValueError("Bookmark host is required")

        return cls(
            host=host,
            username=username,
            port=_optional_int(data.get("port")),
            key_path=key_path,
            alias=alias,
            description=description,
            entry_type=entry_type,
            tunnel_alias=tunnel_alias,
            local_bind_host=_optional_text(data.get("local_bind_host")),
            local_port=_optional_int(data.get("local_port")),
            remote_host=_optional_text(data.get("remote_host")),
            remote_port=_optional_int(data.get("remote_port")),
        )

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "username": self.username,
            "port": self.port,
            "key_path": self.key_path,
            "alias": self.alias,
            "description": self.description,
            "entry_type": self.entry_type,
            "tunnel_alias": self.tunnel_alias,
            "local_bind_host": self.local_bind_host,
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
        }

    @property
    def display_name(self) -> str:
        return self.alias or self.connection_target

    @property
    def connection_target(self) -> str:
        if self.username and "@" not in self.host:
            return f"{self.username}@{self.host}"
        return self.host

    @property
    def is_tunnel(self) -> bool:
        return self.entry_type == "tunnel"

    @property
    def has_tunnel(self) -> bool:
        return self.tunnel_spec is not None

    @property
    def tunnel_display_name(self) -> str | None:
        return self.tunnel_alias or (self.alias if self.is_tunnel else None)

    @property
    def tunnel_spec(self) -> str | None:
        if (
            not self.local_bind_host
            or not self.local_port
            or not self.remote_host
            or not self.remote_port
        ):
            return None
        return (
            f"{self.local_bind_host}:{self.local_port}:"
            f"{self.remote_host}:{self.remote_port}"
        )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
