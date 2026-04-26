# scripts/

Repo-level Python scripts. Cross-platform (no PowerShell).

## `link_packages.py`

Mirrors `packages/<name>/` primitives into `.claude/agents/`,
`.claude/skills/`, `.claude/commands/`, `.github/agents/`, and
`.github/prompts/` via relative symlinks. The canonical source is
`packages/<name>/<platform>/...`; the publish targets exist so this repo's
own Claude Code and Copilot can pick the packages up.

```bash
python scripts/link_packages.py check    # report drift, non-zero on drift
python scripts/link_packages.py sync     # create/repair symlinks (idempotent)
python scripts/link_packages.py repair   # post-clone fix for Windows fallbacks
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
