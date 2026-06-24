# sshj

`sshj` is a Python + Textual SSH bookmark manager.

It gives you a terminal UI to manage bookmarks and a direct connect mode:

- `sshj` opens the TUI app
- `sshj <alias>` connects directly to a saved alias

## Features

- Bookmark fields:
  - entry type: SSH connection or SSH tunnel
  - host/IP (required)
  - username (optional)
  - port (optional)
  - SSH key path (optional)
  - configured SSH key picker from `~/.ssh/config` `IdentityFile` values
  - tunnel forwarding fields for SSH tunnel entries
  - alias (optional)
  - description (optional)
- Connect to a selected bookmark directly from the app
- Start SSH tunnels from the app and watch the live tunnel log/status
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
- `Ctrl+X` stop an active tunnel
- `q` quit

Direct connect by alias:

```bash
sshj my-alias
```

List bookmarks:

```bash
sshj --list
```

## SSH keys

The key picker reads `IdentityFile` entries from:

```bash
~/.ssh/config
~/.ssh/config.d/*
```

Pick a configured key from the dropdown, or leave it on `Manual / no key` and type a custom path into the SSH key field.

## SSH tunnels

Set the entry type to `SSH tunnel` to create entries like:

```bash
ssh -N -L 127.0.0.1:6443:<K8S_API_PRIVATE_HOST>:6443 deploy@<BASTION_HOST>
```

Use these fields:

- Host / IP: bastion host
- Username: SSH user, for example `deploy`
- Local bind host: usually `127.0.0.1`
- Local port: local port to open, for example `6443`
- Private remote host: the host reachable from the bastion, for example the private Kubernetes API host
- Private remote port: remote service port, for example `6443`

Starting a tunnel from the app keeps the UI open and writes status/output to the tunnel log panel. Running `sshj <alias>` for a tunnel alias starts the tunnel directly in the terminal.

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
