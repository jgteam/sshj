from __future__ import annotations

import glob
import shlex
from pathlib import Path


def discover_identity_files() -> list[str]:
    """Return IdentityFile values found in the user's SSH config files."""
    discovered: list[str] = []
    seen: set[str] = set()
    visited_configs: set[Path] = set()

    default_paths = [
        Path.home() / ".ssh" / "config",
        *sorted((Path.home() / ".ssh" / "config.d").glob("*")),
    ]
    for path in default_paths:
        _read_config(path, discovered, seen, visited_configs)

    return discovered


def _read_config(
    path: Path,
    discovered: list[str],
    seen: set[str],
    visited_configs: set[Path],
) -> None:
    if not path.is_file():
        return

    resolved_path = path.expanduser().resolve()
    if resolved_path in visited_configs:
        return
    visited_configs.add(resolved_path)

    for line in resolved_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        try:
            parts = shlex.split(stripped, comments=True)
        except ValueError:
            continue
        if len(parts) < 2:
            continue

        keyword = parts[0].lower()
        if keyword == "identityfile":
            _add_identity_file(parts[1], discovered, seen)
        elif keyword == "include":
            for pattern in parts[1:]:
                for included in _expand_include(pattern, resolved_path.parent):
                    _read_config(included, discovered, seen, visited_configs)


def _add_identity_file(value: str, discovered: list[str], seen: set[str]) -> None:
    resolved = str(Path(value).expanduser())
    if resolved not in seen:
        seen.add(resolved)
        discovered.append(resolved)


def _expand_include(pattern: str, config_dir: Path) -> list[Path]:
    expanded = Path(pattern).expanduser()
    if not expanded.is_absolute():
        expanded = config_dir / expanded

    matches = sorted(glob.glob(str(expanded)))
    return [Path(match) for match in matches]
