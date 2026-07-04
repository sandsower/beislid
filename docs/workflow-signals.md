# workflow_signals

Local workflow-state fan-out.
Beislið skills and host hooks emit normalized states (`working`, `blocked`, `waiting`, `verify`, `review`, `done`, `explore`); sinks consume them best-effort.
In v1 the executable sink is `tmux-glance`, which annotates the current tmux window with a glanceable state icon.
Signals are local presence/status events, not tracker writes or quality gates.
A failed or unavailable sink never blocks workflow progress.

## Two emitters

1. **Skill emissions** happen at semantic phase boundaries (`ready-for-review` phase transitions, `poke-holes` interview states).
   They carry `--skill` and `--phase` context, but they only fire when the model follows the instruction, and only the skills that declare them emit at all.
2. **Host heartbeat hook** (`hooks/workflow_signals.py`, opt-in) emits model-independent signals at Claude Code lifecycle events:

   | Event | State | Meaning |
   |---|---|---|
   | `UserPromptSubmit` | `working` | the user handed the agent work |
   | `Stop` | `waiting` | the agent finished its turn and is waiting on the user |
   | `SessionEnd` | `done` | session over; also runs `tmux-glance clear` |

   The heartbeat is what keeps the panel truthful when a run aborts, a skill forgets to emit, or a skill has no signal instructions at all.
   Skill emissions overwrite heartbeat state at their own boundaries and add the richer context.

The hook only fires inside a git worktree whose root has `.beislid/workflow.md`, so unrelated repos never accumulate signal state.

## Enable the heartbeat hook

1. Install with the flag:

   ```
   ~/Projects/beislid/install.sh --with-signal-hooks
   ```

   Requires `python3` on PATH.
   `workflow_signals.py` is symlinked into `~/.claude/hooks/`.

2. Register the hook in `~/.claude/settings.json`:

   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "python3 $HOME/.claude/hooks/workflow_signals.py",
               "timeout": 5
             }
           ]
         }
       ],
       "Stop": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "python3 $HOME/.claude/hooks/workflow_signals.py",
               "timeout": 5
             }
           ]
         }
       ],
       "SessionEnd": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "python3 $HOME/.claude/hooks/workflow_signals.py",
               "timeout": 5
             }
           ]
         }
       ]
     }
   }
   ```

3. Restart Claude Code.

Other hosts: Pi's managed Beislið wrapper already surfaces signals in its status/title UI; hosts without lifecycle hooks fall back to skill emissions only.

## File sink and staleness

Every emit also writes a file sink under `${BEISLID_STATE_DIR:-~/.local/state/beislid}/signals/<repo_hash>/<branch_slug>` for external consumers.
`done` removes the file, so a missing file means idle.
Runs that end without `done` (aborts, crashes, sessions predating the heartbeat hook) leave stale files behind.

Inspect and clean:

```
beislid workflow-signal status                 # shows the current branch's signal and flags entries older than 24h
beislid workflow-signal sweep                  # removes signal files older than 24h
beislid workflow-signal sweep --max-age-hours 4
```

## Configure

The `beislid:workflow_signals` block in `.beislid/workflow.md` gates the sink fan-out (see `workflow-md-format.md` for the grammar):

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
```

`mode: off` disables sink fan-out; the file sink still records state for external consumers.
Per-skill overrides go under an optional `skills:` map.
The heartbeat hook needs no config beyond the block existing; it emits without `--skill`, so the repo-level `mode` applies.
