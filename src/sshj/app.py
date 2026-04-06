from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from sshj.models import Bookmark
from sshj.storage import BookmarkStorage


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

    #bookmark_list {
        height: 1fr;
        border: round $accent;
        margin-bottom: 1;
    }

    .form-label {
        margin-top: 1;
    }

    #save {
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
        ("q", "quit", "Quit"),
    ]

    def __init__(self, storage: BookmarkStorage) -> None:
        super().__init__()
        self.storage = storage
        self.bookmarks: list[Bookmark] = []
        self.selected_index: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="left-pane"):
                yield Static("Saved Bookmarks", classes="section-title")
                yield ListView(id="bookmark_list")
                with Horizontal():
                    yield Button("New", id="new")
                    yield Button("Delete", id="delete", variant="error")
                    yield Button("Connect", id="connect", variant="success")
            with Vertical(id="right-pane"):
                yield Static("Bookmark Details", classes="section-title")
                yield Label("Host / IP *", classes="form-label")
                yield Input(placeholder="example.com", id="host")
                yield Label("Username (optional)", classes="form-label")
                yield Input(placeholder="ubuntu", id="username")
                yield Label("Port (optional)", classes="form-label")
                yield Input(placeholder="22", id="port")
                yield Label("SSH key path (optional)", classes="form-label")
                yield Input(placeholder="~/.ssh/id_ed25519", id="key")
                yield Label("Alias (optional)", classes="form-label")
                yield Input(placeholder="prod-db", id="alias")
                yield Label("Description (optional)", classes="form-label")
                yield Input(placeholder="Production database", id="description")
                yield Button("Save", id="save", variant="primary")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "new":
            self.action_new_bookmark()
        elif button_id == "save":
            self.action_save_bookmark()
        elif button_id == "delete":
            self.action_delete_bookmark()
        elif button_id == "connect":
            self.action_connect_current()

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

    def action_connect_current(self) -> None:
        bookmark = self._bookmark_from_form(
            ignore_index=self.selected_index,
            enforce_unique_alias=False,
        )
        if bookmark is None:
            return

        self._set_status(f"Connecting to {bookmark.connection_target}...")
        self.exit(bookmark)

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
        self.query_one("#key", Input).value = bookmark.key_path or ""
        self.query_one("#alias", Input).value = bookmark.alias or ""
        self.query_one("#description", Input).value = bookmark.description or ""

    def _clear_form(self) -> None:
        self.query_one("#host", Input).value = ""
        self.query_one("#username", Input).value = ""
        self.query_one("#port", Input).value = ""
        self.query_one("#key", Input).value = ""
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
        port_value = self.query_one("#port", Input).value.strip()
        port: int | None = None
        if port_value:
            if not port_value.isdigit():
                self._set_status("Port must be a number.", error=True)
                return None
            parsed_port = int(port_value)
            if not 1 <= parsed_port <= 65535:
                self._set_status("Port must be between 1 and 65535.", error=True)
                return None
            port = parsed_port

        key_path = self.query_one("#key", Input).value.strip() or None
        alias = self.query_one("#alias", Input).value.strip() or None
        description = self.query_one("#description", Input).value.strip() or None

        if alias and enforce_unique_alias:
            for index, existing in enumerate(self.bookmarks):
                if index == ignore_index:
                    continue
                if existing.alias == alias:
                    self._set_status(f"Alias '{alias}' already exists.", error=True)
                    return None

        return Bookmark(
            host=host,
            username=username,
            port=port,
            key_path=key_path,
            alias=alias,
            description=description,
        )

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
        return f"{alias} -> {bookmark.connection_target}{port}{description}"
