from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class KubeconfigEntry:
    name: str
    path: str

    @classmethod
    def from_dict(cls, data: dict) -> "KubeconfigEntry":
        name = str(data.get("name") or "").strip()
        path = str(data.get("path") or "").strip()
        if not name or not path or not Path(path).expanduser().is_absolute():
            raise ValueError("Kubeconfig name and path are required")
        return cls(name=name, path=path)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "path": self.path}

    @property
    def expanded_path(self) -> str:
        return str(Path(self.path).expanduser().absolute())
