# scripts/

Repo-level Python scripts. Cross-platform (no PowerShell).

## `link_agents.py`

Mirrors `agents/<name>/` into `.github/agents/` via relative symlinks.
The canonical source is `agents/<name>/`; `.github/agents/` exists so
this repo's own Copilot can pick the agents up.

```bash
python scripts/link_agents.py check    # report drift, non-zero on drift
python scripts/link_agents.py sync     # create/repair symlinks (idempotent)
python scripts/link_agents.py repair   # post-clone fix for Windows fallbacks
```

`check` runs in CI. `sync` is the day-to-day command after authoring or
adopting a new agent. `repair` is the recovery command after cloning on
Windows without `core.symlinks=true`.

### Windows prerequisites

Symlinks on Windows require either:

- **Developer Mode** (Settings → Privacy & security → For developers →
  Developer Mode), or
- running git/python as an administrator.

Also set `git config --global core.symlinks true` so symlinks come
through clones intact rather than being materialized as text files.

See `docs/development.md` for the full setup notes.
