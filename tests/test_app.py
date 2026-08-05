from __future__ import annotations

import asyncio

from textual.widgets import Input

from sshj.app import SSHJApp
from sshj.storage import BookmarkStorage


def test_save_new_bookmark_without_tunnel(tmp_path) -> None:
    async def run_test() -> None:
        storage = BookmarkStorage(tmp_path / "bookmarks.json")
        app = SSHJApp(storage)

        async with app.run_test(size=(120, 90)) as pilot:
            app.action_new_bookmark()
            app.query_one("#host", Input).value = "example.com"
            app.query_one("#alias", Input).value = "example"

            await pilot.click("#save")
            await pilot.pause()

            assert len(app.bookmarks) == 1
            assert app.bookmarks[0].host == "example.com"
            assert app.bookmarks[0].alias == "example"
            assert app.bookmarks[0].local_bind_host is None
            assert storage.load() == app.bookmarks

    asyncio.run(run_test())
