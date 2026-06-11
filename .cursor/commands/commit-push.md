# Commit and push

Commit all current changes and push them to the remote repository.

## Steps

1. Run in parallel:
   - `git status` — list untracked and modified files
   - `git diff` — unstaged changes
   - `git diff --staged` — staged changes (if any)
   - `git log --oneline -10` — commit message style in the repo

2. Analyze changes and draft a commit message:
   - 1–2 sentences, focus on *why*, not *what*
   - Accurately reflect the change: feature / fix / refactor / test / docs, etc.
   - Do not include secret files (`.env`, credentials, etc.) — warn the user if present

3. If there are no changes — report that and stop.

4. Stage all relevant files (`git add`).

5. Create the commit:

```bash
git commit -m "$(cat <<'EOF'
Commit message here.

EOF
)"
```

6. If the commit is rejected by a pre-commit hook — fix the issue and create a **new** commit (do not amend).

7. Check branch state:

```bash
git status
```

8. Push to remote:
   - If the branch does not track a remote yet: `git push -u origin HEAD`
   - Otherwise: `git push`
   - **Never** run `git push --force` on `main`/`master`

9. After push, run `git status` and briefly report:
   - what was committed
   - where it was pushed (branch, remote)
   - any issues encountered

## Constraints

- Do not change `git config`
- Do not use destructive commands (`reset --hard`, force push, etc.)
- Do not skip hooks (`--no-verify`)
- Do not amend if the commit was already pushed
