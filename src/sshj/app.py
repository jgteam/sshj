from __future__ import annotations

import asyncio
import shlex

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Select,
    Static,
)

from sshj.models import Bookmark
from sshj.ssh import build_tunnel_command
from sshj.ssh_config import discover_identity_files
from sshj.storage import BookmarkStorage


MANUAL_KEY = "__manual__"


class SSHJApp(App[Bookmark | None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #left-pane,
    #right-pane {
        width: 1fr;
        padding: 1 2;
        border: round $panel;
        margin: 0 1;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .subsection-title {
        text-style: bold;
        margin-top: 2;
        margin-bottom: 1;
    }

    #bookmark_list {
        height: 1fr;
        border: round $accent;
        margin-bottom: 1;
    }

    .form-label {
        margin-top: 1;
    }

    .button-row {
        height: 3;
        min-height: 3;
        margin-top: 1;
    }

    .button-row Button {
        width: 1fr;
        min-width: 12;
        height: 3;
    }

    #tunnel-log {
        height: 10;
        border: round $accent;
        margin-top: 1;
    }

    #form-actions {
        margin-top: 2;
    }

    #status {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $surface;
    }
    """

    BINDINGS = [
        ("ctrl+n", "new_bookmark", "New"),
        ("ctrl+s", "save_bookmark", "Save"),
        ("ctrl+d", "delete_bookmark", "Delete"),
        ("ctrl+e", "connect_current", "Connect"),
        ("ctrl+t", "start_tunnel_current", "Start Tunnel"),
        ("ctrl+x", "stop_tunnel", "Stop Tunnel"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, storage: BookmarkStorage) -> None:
        super().__init__()
        self.storage = storage
        self.bookmarks: list[Bookmark] = []
        self.identity_files: list[str] = []
        self.selected_index: int | None = None
        self.active_tunnel: asyncio.subprocess.Process | None = None
        self.tunnel_task: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="left-pane"):
                yield Static("Saved Bookmarks", classes="section-title")
                yield ListView(id="bookmark_list")
                with Horizontal(classes="button-row"):
                    yield Button("New", id="new")
                    yield Button("Delete", id="delete", variant="error")
                with Horizontal(classes="button-row"):
                    yield Button("Connect SSH", id="connect", variant="success")
                    yield Button("Start Tunnel", id="start_tunnel", variant="warning")
            with VerticalScroll(id="right-pane"):
                yield Static("Bookmark Details", classes="section-title")
                yield Label("Host / IP *", classes="form-label")
                yield Input(placeholder="example.com", id="host")
                yield Label("Username (optional)", classes="form-label")
                yield Input(placeholder="ubuntu", id="username")
                yield Label("Port (optional)", classes="form-label")
                yield Input(placeholder="22", id="port")
                yield Label("Configured SSH key", classes="form-label")
                yield Select(
                    [(self._key_label(MANUAL_KEY), MANUAL_KEY)],
                    id="key_select",
                    prompt="Select key from SSH config",
                    allow_blank=False,
                    value=MANUAL_KEY,
                )
                yield Label("SSH key path (optional)", classes="form-label")
                yield Input(placeholder="~/.ssh/id_ed25519", id="key")
                yield Label("Alias (optional)", classes="form-label")
                yield Input(placeholder="prod-db", id="alias")
                yield Label("Description (optional)", classes="form-label")
                yield Input(placeholder="Production database", id="description")
                yield Static("Tunnel Details (optional)", classes="subsection-title")
                yield Label("Tunnel alias", classes="form-label")
                yield Input(placeholder="prod-k8s", id="tunnel_alias")
                yield Label("Local bind host", classes="form-label")
                yield Input(placeholder="127.0.0.1", id="local_bind_host")
                yield Label("Local port", classes="form-label")
                yield Input(placeholder="6443", id="local_port")
                yield Label("Private remote host", classes="form-label")
                yield Input(placeholder="k8s-api.internal", id="remote_host")
                yield Label("Private remote port", classes="form-label")
                yield Input(placeholder="6443", id="remote_port")
                with Horizontal(id="form-actions", classes="button-row"):
                    yield Button("Save", id="save", variant="primary")
                    yield Button("Start Tunnel", id="start_tunnel_form", variant="warning")
                    yield Button("Stop Tunnel", id="stop_tunnel", variant="warning")
                yield Static("Tunnel log", classes="section-title")
                yield RichLog(id="tunnel-log", wrap=True, highlight=True)
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.identity_files = discover_identity_files()
        self._refresh_key_options()
        try:
            self.bookmarks = self.storage.load()
        except Exception as error:  # pragma: no cover - defensive UI fallback
            self.bookmarks = []
            self._set_status(f"Could not load bookmarks: {error}", error=True)
            return
        self._refresh_list()
        self._set_status(
            f"Loaded {len(self.bookmarks)} bookmark(s). Press Ctrl+N to create a new one."
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "new":
            self.action_new_bookmark()
        elif button_id == "save":
            self.action_save_bookmark()
        elif button_id == "delete":
            self.action_delete_bookmark()
        elif button_id == "connect":
            await self.action_connect_current()
        elif button_id in ("start_tunnel", "start_tunnel_form"):
            await self.action_start_tunnel_current()
        elif button_id == "stop_tunnel":
            await self.action_stop_tunnel()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "key_select" and event.value != MANUAL_KEY:
            self.query_one("#key", Input).value = str(event.value)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.bookmarks):
            self._load_bookmark(index)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.bookmarks):
            self._load_bookmark(index)

    def action_new_bookmark(self) -> None:
        self.selected_index = None
        self._clear_form()
        self.query_one("#host", Input).focus()
        self._set_status("Creating a new bookmark.")

    def action_save_bookmark(self) -> None:
        bookmark = self._bookmark_from_form(
            ignore_index=self.selected_index,
            enforce_unique_alias=True,
        )
        if bookmark is None:
            return

        if self.selected_index is None:
            self.bookmarks.append(bookmark)
            self.selected_index = len(self.bookmarks) - 1
            action = "created"
        else:
            self.bookmarks[self.selected_index] = bookmark
            action = "updated"

        self.storage.save(self.bookmarks)
        self._refresh_list(select_index=self.selected_index)
        self._set_status(f"Bookmark {action}.")

    def action_delete_bookmark(self) -> None:
        if self.selected_index is None:
            self._set_status("Select a bookmark to delete.", error=True)
            return

        self.bookmarks.pop(self.selected_index)
        self.storage.save(self.bookmarks)

        next_index = None
        if self.bookmarks:
            next_index = min(self.selected_index, len(self.bookmarks) - 1)

        self._refresh_list(select_index=next_index)
        self._set_status("Bookmark deleted.")

    async def action_connect_current(self) -> None:
        bookmark = self._bookmark_from_form(
            ignore_index=self.selected_index,
            enforce_unique_alias=False,
        )
        if bookmark is None:
            return

        self._set_status(f"Connecting to {bookmark.connection_target}...")
        self.exit(bookmark)

    async def action_start_tunnel_current(self) -> None:
        bookmark = self._bookmark_from_form(
            ignore_index=self.selected_index,
            enforce_unique_alias=False,
        )
        if bookmark is None:
            return

        if not bookmark.has_tunnel:
            self._set_status("Fill the tunnel fields first, then save/start the tunnel.", error=True)
            return

        await self._start_tunnel(bookmark)

    async def action_stop_tunnel(self) -> None:
        await self._stop_tunnel()

    def _refresh_list(self, select_index: int | None = None) -> None:
        list_view = self.query_one("#bookmark_list", ListView)

        for child in list(list_view.children):
            child.remove()

        for index, bookmark in enumerate(self.bookmarks):
            label = self._format_bookmark(index, bookmark)
            list_view.append(ListItem(Label(label)))

        if not self.bookmarks:
            self.selected_index = None
            self._clear_form()
            return

        target_index = select_index
        if target_index is None:
            target_index = 0
        if target_index < 0 or target_index >= len(self.bookmarks):
            target_index = 0

        list_view.index = target_index
        self._load_bookmark(target_index)

    def _load_bookmark(self, index: int) -> None:
        bookmark = self.bookmarks[index]
        self.selected_index = index

        self.query_one("#host", Input).value = bookmark.host
        self.query_one("#username", Input).value = bookmark.username or ""
        self.query_one("#port", Input).value = "" if bookmark.port is None else str(bookmark.port)
        self._select_key(bookmark.key_path)
        self.query_one("#key", Input).value = bookmark.key_path or ""
        self.query_one("#tunnel_alias", Input).value = bookmark.tunnel_alias or ""
        self.query_one("#local_bind_host", Input).value = bookmark.local_bind_host or "127.0.0.1"
        self.query_one("#local_port", Input).value = (
            "" if bookmark.local_port is None else str(bookmark.local_port)
        )
        self.query_one("#remote_host", Input).value = bookmark.remote_host or ""
        self.query_one("#remote_port", Input).value = (
            "" if bookmark.remote_port is None else str(bookmark.remote_port)
        )
        self.query_one("#alias", Input).value = bookmark.alias or ""
        self.query_one("#description", Input).value = bookmark.description or ""

    def _clear_form(self) -> None:
        self.query_one("#host", Input).value = ""
        self.query_one("#username", Input).value = ""
        self.query_one("#port", Input).value = ""
        self.query_one("#key_select", Select).value = MANUAL_KEY
        self.query_one("#key", Input).value = ""
        self.query_one("#tunnel_alias", Input).value = ""
        self.query_one("#local_bind_host", Input).value = "127.0.0.1"
        self.query_one("#local_port", Input).value = ""
        self.query_one("#remote_host", Input).value = ""
        self.query_one("#remote_port", Input).value = ""
        self.query_one("#alias", Input).value = ""
        self.query_one("#description", Input).value = ""

    def _bookmark_from_form(
        self,
        ignore_index: int | None,
        enforce_unique_alias: bool,
    ) -> Bookmark | None:
        host = self.query_one("#host", Input).value.strip()
        if not host:
            self._set_status("Host / IP is required.", error=True)
            return None

        username = self.query_one("#username", Input).value.strip() or None
        port = self._parse_port("#port", "Port")
        if port is None and self.query_one("#port", Input).value.strip():
            return None

        key_path = self.query_one("#key", Input).value.strip() or None
        tunnel_alias = self.query_one("#tunnel_alias", Input).value.strip() or None
        local_port_value = self.query_one("#local_port", Input).value.strip()
        remote_port_value = self.query_one("#remote_port", Input).value.strip()
        local_bind_host = self.query_one("#local_bind_host", Input).value.strip() or None
        local_port = self._parse_port("#local_port", "Local port")
        if local_port is None and local_port_value:
            return None
        remote_host = self.query_one("#remote_host", Input).value.strip() or None
        remote_port = self._parse_port("#remote_port", "Private remote port")
        if remote_port is None and remote_port_value:
            return None
        alias = self.query_one("#alias", Input).value.strip() or None
        description = self.query_one("#description", Input).value.strip() or None
        has_any_tunnel_field = any(
            [tunnel_alias, local_port_value, remote_host, remote_port_value]
        ) or local_bind_host not in (None, "127.0.0.1")

        if has_any_tunnel_field:
            if not tunnel_alias:
                self._set_status("Tunnel alias is required when a tunnel is configured.", error=True)
                return None
            if not local_bind_host:
                self._set_status("Local bind host is required for tunnels.", error=True)
                return None
            if local_port is None:
                self._set_status("Local port is required for tunnels.", error=True)
                return None
            if not remote_host:
                self._set_status("Private remote host is required for tunnels.", error=True)
                return None
            if remote_port is None:
                self._set_status("Private remote port is required for tunnels.", error=True)
                return None
        else:
            # The new-entry form supplies this convenience default, but it does not
            # mean the user configured a tunnel.
            local_bind_host = None

        if alias and tunnel_alias and alias == tunnel_alias:
            self._set_status("SSH alias and tunnel alias must be different.", error=True)
            return None

        if enforce_unique_alias and not self._aliases_are_unique(alias, tunnel_alias, ignore_index):
            return None

        return Bookmark(
            host=host,
            username=username,
            port=port,
            key_path=key_path,
            alias=alias,
            description=description,
            entry_type="ssh",
            tunnel_alias=tunnel_alias,
            local_bind_host=local_bind_host,
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
        )

    def _parse_port(self, selector: str, label: str) -> int | None:
        value = self.query_one(selector, Input).value.strip()
        if not value:
            return None
        if not value.isdigit():
            self._set_status(f"{label} must be a number.", error=True)
            return None

        port = int(value)
        if not 1 <= port <= 65535:
            self._set_status(f"{label} must be between 1 and 65535.", error=True)
            return None
        return port

    def _refresh_key_options(self) -> None:
        key_select = self.query_one("#key_select", Select)
        options = [(self._key_label(MANUAL_KEY), MANUAL_KEY)]
        options.extend((self._key_label(path), path) for path in self.identity_files)
        key_select.set_options(options)
        key_select.value = MANUAL_KEY

    def _select_key(self, key_path: str | None) -> None:
        key_select = self.query_one("#key_select", Select)
        if key_path and key_path in self.identity_files:
            key_select.value = key_path
        else:
            key_select.value = MANUAL_KEY

    def _aliases_are_unique(
        self,
        alias: str | None,
        tunnel_alias: str | None,
        ignore_index: int | None,
    ) -> bool:
        aliases_to_check = [
            (alias, "SSH alias"),
            (tunnel_alias, "Tunnel alias"),
        ]
        for current_alias, label in aliases_to_check:
            if not current_alias:
                continue
            for index, existing in enumerate(self.bookmarks):
                if index == ignore_index:
                    continue
                if existing.alias == current_alias:
                    self._set_status(f"{label} '{current_alias}' already exists.", error=True)
                    return False
                if existing.tunnel_alias == current_alias:
                    self._set_status(f"{label} '{current_alias}' already exists as a tunnel alias.", error=True)
                    return False
        return True

    async def _start_tunnel(self, bookmark: Bookmark) -> None:
        if self.active_tunnel and self.active_tunnel.returncode is None:
            self._set_status("A tunnel is already running. Stop it before starting another.", error=True)
            return

        try:
            command = build_tunnel_command(bookmark)
        except ValueError as error:
            self._set_status(str(error), error=True)
            return

        log = self.query_one("#tunnel-log", RichLog)
        log.clear()
        self._write_log(f"Starting tunnel: {bookmark.display_name}")
        self._write_log("$ " + shlex.join(command))

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as error:
            self._set_status(f"Could not start tunnel: {error}", error=True)
            self._write_log(f"Failed to start tunnel: {error}")
            return

        self.active_tunnel = process
        self.tunnel_task = asyncio.create_task(self._watch_tunnel(process))
        await asyncio.sleep(1)

        if process.returncode is None:
            self._set_status(f"Tunnel active: {bookmark.tunnel_spec}")
            self._write_log(f"Tunnel active: {bookmark.tunnel_spec}")

    async def _watch_tunnel(self, process: asyncio.subprocess.Process) -> None:
        tasks = []
        if process.stdout:
            tasks.append(asyncio.create_task(self._read_stream(process.stdout, "stdout")))
        if process.stderr:
            tasks.append(asyncio.create_task(self._read_stream(process.stderr, "stderr")))

        return_code = await process.wait()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if self.active_tunnel is process:
            self.active_tunnel = None
            self._set_status(f"Tunnel stopped with exit code {return_code}.")
        self._write_log(f"Tunnel stopped with exit code {return_code}.")

    async def _read_stream(self, stream: asyncio.StreamReader, name: str) -> None:
        while line := await stream.readline():
            text = line.decode(errors="replace").rstrip()
            if text:
                self._write_log(f"{name}: {text}")

    async def _stop_tunnel(self) -> None:
        if not self.active_tunnel or self.active_tunnel.returncode is not None:
            self._set_status("No active tunnel to stop.")
            return

        self._write_log("Stopping tunnel...")
        self.active_tunnel.terminate()
        try:
            await asyncio.wait_for(self.active_tunnel.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._write_log("Tunnel did not exit after SIGTERM; killing it.")
            self.active_tunnel.kill()
            await self.active_tunnel.wait()

    def _write_log(self, message: str) -> None:
        self.query_one("#tunnel-log", RichLog).write(message)

    def _set_status(self, message: str, *, error: bool = False) -> None:
        status = self.query_one("#status", Static)
        if error:
            status.update(f"Error: {message}")
        else:
            status.update(message)

    @staticmethod
    def _format_bookmark(index: int, bookmark: Bookmark) -> str:
        alias = bookmark.alias or f"bookmark-{index + 1}"
        port = f":{bookmark.port}" if bookmark.port else ""
        description = f" - {bookmark.description}" if bookmark.description else ""
        tunnel = ""
        if bookmark.has_tunnel:
            tunnel_alias = bookmark.tunnel_display_name or "no-tunnel-alias"
            tunnel = f" | tunnel {tunnel_alias}: {bookmark.tunnel_spec}"
        return f"[SSH] {alias} -> {bookmark.connection_target}{port}{description}{tunnel}"

    @staticmethod
    def _key_label(value: str) -> str:
        if value == MANUAL_KEY:
            return "Manual / no key"
        return value

    async def on_unmount(self) -> None:
        if self.tunnel_task and not self.tunnel_task.done():
            self.tunnel_task.cancel()
        if self.active_tunnel and self.active_tunnel.returncode is None:
            self.active_tunnel.terminate()
            try:
                await asyncio.wait_for(self.active_tunnel.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.active_tunnel.kill()
                await self.active_tunnel.wait()
