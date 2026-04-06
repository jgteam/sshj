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

    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        host = str(data.get("host", "")).strip()
        username = _optional_text(data.get("username"))
        port = data.get("port")
        key_path = _optional_text(data.get("key_path"))
        alias = _optional_text(data.get("alias"))
        description = _optional_text(data.get("description"))

        parsed_port: int | None
        if port in (None, ""):
            parsed_port = None
        else:
            parsed_port = int(port)

        if not host:
            raise ValueError("Bookmark host is required")

        return cls(
            host=host,
            username=username,
            port=parsed_port,
            key_path=key_path,
            alias=alias,
            description=description,
        )

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "username": self.username,
            "port": self.port,
            "key_path": self.key_path,
            "alias": self.alias,
            "description": self.description,
        }

    @property
    def display_name(self) -> str:
        return self.alias or self.connection_target

    @property
    def connection_target(self) -> str:
        if self.username and "@" not in self.host:
            return f"{self.username}@{self.host}"
        return self.host


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
