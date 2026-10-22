from __future__ import annotations

import asyncio

from textual.widgets import Input, TabbedContent

from sshj.app import SSHJApp
from sshj.storage import BookmarkStorage, KubeconfigStorage


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


def test_kubeconfig_tab_create_edit_delete_and_casefold_name(tmp_path) -> None:
    async def run_test() -> None:
        bookmarks = BookmarkStorage(tmp_path / "bookmarks.json")
        kubeconfigs = KubeconfigStorage(tmp_path / "kubeconfigs.json")
        app = SSHJApp(bookmarks, kubeconfigs)

        async with app.run_test(size=(120, 90)) as pilot:
            app.query_one(TabbedContent).active = "kubeconfig-tab"
            await pilot.pause()
            await pilot.click("#new_kubeconfig")
            app.query_one("#kubeconfig_name", Input).value = "CP-01"
            app.query_one("#kubeconfig_path", Input).value = "/tmp/kubeconfig-cp-01.yaml"
            await pilot.click("#save_kubeconfig")
            await pilot.pause()

            assert len(app.kubeconfigs) == 1
            assert kubeconfigs.load() == app.kubeconfigs

            app.action_new_kubeconfig()
            app.query_one("#kubeconfig_name", Input).value = "cp-01"
            app.query_one("#kubeconfig_path", Input).value = "/tmp/duplicate.yaml"
            app.action_save_kubeconfig()
            assert len(app.kubeconfigs) == 1

            app._load_kubeconfig(0)
            app.query_one("#kubeconfig_path", Input).value = "/tmp/updated.yaml"
            await pilot.click("#save_kubeconfig")
            assert kubeconfigs.load()[0].path == "/tmp/updated.yaml"

            await pilot.click("#delete_kubeconfig")
            assert kubeconfigs.load() == []
            assert bookmarks.load() == []

    asyncio.run(run_test())
