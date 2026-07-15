# setup update v1

In verbose mode, emit `✓ setup/update v1 loaded` immediately after reading this file.

If the invocation includes update intent (`setup update`, `/setup update`, `update beislid`, or equivalent), do not enter project-config setup and do not read or write `<repo>/.beislid/workflow.md`.

Run this distribution-update flow instead:

1. Resolve the install manifest path: `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/install.json`.
2. Read the manifest.
  If missing, hard-fail with:

   ```text
   🛑 No Beislið install manifest found at `<manifest>`. Run `install.sh --update`
   from your Beislið checkout, or reinstall Beislið with `<beislid-repo>/install.sh`.
   ```

3. Read `repo` from the manifest.
  If empty, missing, or not a directory, hard-fail with:

   ```text
   🛑 Beislið install manifest does not point at a valid repo: `<repo>`.
   Run `install.sh --update` from your Beislið checkout, or reinstall Beislið.
   ```

4. Check `<repo>/install.sh` exists and is executable.
  If not, hard-fail with the same recovery guidance.
5. Show the planned action and ask for confirmation:

   ```text
   📋 Update Beislið from `<repo>`?

   This will run:
   `<repo>/install.sh --update`

   The installer will abort if the Beislið checkout has uncommitted changes,
   preserve prior install targets and opt-ins from the manifest, fast-forward
   with `git pull --ff-only`, then relink skills/hooks as needed.

   Proceed? [Y/n]
   ```

6. On `n`, exit cleanly without running anything.
  On `Y`, run `<repo>/install.sh --update` and stream output.
  Report success or failure with the command's exit code.

Tripwires:

- Update mode never modifies project-owned `.beislid/workflow.md`.
- Do not infer the install repo from skill symlinks; the manifest `repo` field is authoritative.
- Do not add `--force` unless the user explicitly asks for it in the same update request.
