# setup section visual-surfaces v1

In verbose mode, emit `✓ setup/section-visual-surfaces v1 loaded` immediately after reading this file.

## Visual surfaces

Configure the canonical `beislid:visual_surfaces` block under `Visual surfaces`.
Explain that repo config is required for proactive visual routing; user-level plugin enablement alone is not enough.
The only v1 provider is `lavish-axi`, and doctor validates config shape without deep-invoking Lavish.
Explain that `artifact_retention` affects supplemental `.lavish/` HTML only; `local` is the safe ignored default, `discard` removes wrappers after use, and `preserve-repo` requires explicit publication intent plus a gitignore exception.

Ask:

```text
Configure visual surfaces? (off / suggest / prompt / auto / skip)
```

For any mode except `skip`, ask whether to use the default Lavish command/artifact root/retention or override them.
Defaults are `npx -y lavish-axi`, `.lavish`, and `local`.
If retention is overridden, prompt explicitly for `local`, `discard`, or `preserve-repo`.
Ask for optional per-workflow mode overrides only when the user wants them; valid override values are `off / suggest / prompt / auto`.

```beislid:visual_surfaces
provider: lavish-axi
mode: prompt
command: 'npx -y lavish-axi'
artifact_root: .lavish
artifact_retention: local
workflows:
  spec: prompt
  blueprint: suggest
```

Never create duplicate `beislid:visual_surfaces` blocks; update or remove the existing one.
