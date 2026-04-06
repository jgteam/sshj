# sshj

`sshj` is a Python + Textual SSH bookmark manager.

It gives you a terminal UI to manage bookmarks and a direct connect mode:

- `sshj` opens the TUI app
- `sshj <alias>` connects directly to a saved alias

## Features

- Bookmark fields:
  - host/IP (required)
  - username (optional)
  - port (optional)
  - SSH key path (optional)
  - alias (optional)
  - description (optional)
- Connect to a selected bookmark directly from the app
- Direct alias connect from any terminal via `sshj <alias>`
- JSON storage at `~/.sshj/bookmarks.json` (override with `SSHJ_BOOKMARKS`)

## Install (editable)

```bash
cd /Users/jannisgunsche/PycharmProjects/sshj
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

After this, `sshj` is available while that environment is active.

## iTerm2 + zsh setup (available in every terminal)

iTerm2 uses your shell startup files, so adding `sshj` to `~/.zshrc` makes it available in every new iTerm2 tab/window.

1. Add this line to `~/.zshrc`:

```bash
source /Users/jannisgunsche/PycharmProjects/sshj/shell/sshj.sh

echo 'source /Users/jannisgunsche/PycharmProjects/sshj/shell/sshj.sh' >> ~/.zshrc
source ~/.zshrc
```

2. Reload zsh:

```bash
source ~/.zshrc
```

3. Verify:

```bash
type sshj
sshj --list
```

The sourced helper defines an `sshj` shell function that runs this project directly.
It uses `/Users/jannisgunsche/PycharmProjects/sshj/.venv/bin/python` if present, otherwise `python3` from PATH.

If you use bash in another terminal, add the same `source .../shell/sshj.sh` line to `~/.bashrc`.

## Usage

Open the app:

```bash
sshj
```

Inside the app:

- `Ctrl+N` new bookmark
- `Ctrl+S` save bookmark
- `Ctrl+D` delete bookmark
- `Ctrl+E` connect to the current form/bookmark
- `q` quit

Direct connect by alias:

```bash
sshj my-alias
```

List bookmarks:

```bash
sshj --list
```

## Notes

- Alias is optional for saved entries, but required for `sshj <alias>` direct connect.
- Host should be plain host/IP; set the login user in the `username` field.
- Existing entries with `user@host` in host still work for backward compatibility.

## Troubleshooting

If `pip install -e .` fails inside `.venv` with:

`ERROR: Can not perform a '--user' install. User site-packages are not visible in this virtualenv.`

run:

```bash
python -m pip config unset global.user
```
