# Cross-Workstation Git Sync

`origin/main` is the integrated source of truth. Ubuntu, Windows native, and WSL
use separate clones of the same private remote. Do not maintain permanent OS
branches or copy source trees manually between machines.

## Start a task

```bash
git status
git remote -v
git fetch --prune
git switch main
git pull --ff-only
git switch -c <short-task-branch>
```

If the worktree is dirty, inspect ownership and purpose first. Do not discard,
overwrite, or auto-stash changes that belong to another task. Prefix short-lived
branches by development context, for example `win/openusd-lab`,
`ubuntu/rb-driver`, or `core/geometry-v2`.

## Finish a task

Run the relevant hardware-free tests, then:

```bash
git status
git diff --check
git diff
git add <intentional-files-only>
git diff --cached
git commit -m "<meaningful message>"
git fetch --prune
git rebase origin/main
git push -u origin <short-task-branch>
```

Before pushing, confirm the remote is private, scan the staged diff for secrets,
private network details, company content, binaries, and large data, and rerun
tests after any rebase or conflict resolution.

Never force-push a shared branch. Resolve conflicts in `AGENTS.md`,
`ARCHITECTURE.md`, and `PROJECT_STATE.md` by preserving both machines' newer
facts and decisions; never choose one side wholesale.

## Machine handoff

Meaningful work must be committed and pushed before switching machines. On the
next machine, fetch and inspect the task branch, then continue or integrate it
through normal review. Data bytes follow `docs/data/DATA_POLICY.md`, not Git.
