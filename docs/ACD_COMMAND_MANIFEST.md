# Accodite `acd` command manifest

Internal codespace commands. Use **`git`** only for real GitHub remotes.

## Session
- `acd help` — command list
- `acd status` — repo · cwd · scope
- `acd heartbeat` — sandbox health / writable root

## Repo
- `acd repo <name>` — switch active repo
- `acd rootcheck` — .gsp.json, uid, start_row, cwd, manifest
- `acd pwd` / `acd ls` / `acd cd <path>`

## Files
- `acd eof <path> <text>` — append
- `acd grep <pat> [path]`
- `acd sed <old> <new> <path>`

## GitHub
`git clone|fetch|pull|push|commit` only.

## Persist
Set `ACCD_SANDBOX_ROOT` to a durable volume.
