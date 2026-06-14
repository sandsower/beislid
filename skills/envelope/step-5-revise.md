# envelope step 5 revise v1

Authoritative JIT protocol for envelope Step 5. Load only in revision mode, straight from Step 1 (Steps 2–4 are not run as separate steps; this step reuses their mechanics on the delta).

## Purpose

Produce version N+1 of an existing bundle in place, addressing the feedback from the delivery artifact or bundle status. Supersession is by hash: rondo computes the sha256 of a manifest at load and refuses superseded exports.

## Protocol

Print the Step 5 entry one-liner from `envelope-templates.md`.

### Record the prior hash FIRST

Before touching any file, compute the sha256 of the existing `.beislid/exports/<bundle-id>/bundle.json` (`shasum -a 256` or Python `hashlib`) and record it with the prior `version`. This hash becomes the new bundle's `supersedes`; computing it after a rewrite destroys the chain.

### Re-author the delta

For each envelope named by the feedback, re-author it per `step-2-author.md` mechanics with the feedback as additional planning context. Feedback may also add new envelopes (author fresh) or remove envelopes (apply the Step 3 dependency cascade to dependents). Envelopes untouched by feedback are NOT re-authored.

### Delta summary

Produce a human-readable delta, one line per envelope: `changed` (what and why, tied to the feedback), `new`, `removed` (+ cascade demotions), `unchanged`. Show it before any verdicts.

### Delta-only re-approval

Run `step-3-approve.md` verdicts for changed and new envelopes only. Unchanged approved envelopes carry forward with their ORIGINAL approval metadata (`approved_at`, `approved_by`) — re-approval is not re-litigating settled slices. Zero approved envelopes across carried + re-approved is the fail-closed terminal state; the prior bundle stays untouched.

### Export in place

Follow `step-4-export.md` mechanics with these revision deltas:

- Rewrite the SAME `.beislid/exports/<bundle-id>/` — the collision hard-stop does not apply in revision mode; git history archives the prior version.
- `version`: prior + 1. `supersedes`: the recorded prior-bundle.json sha256. `status: approved`.
- `approval`: timestamp of this revision's verdict sitting; carried-forward slices keep their original metadata in their slice records where present.
- Validate (`beislid export validate`), checkpoint, and commit exactly as Step 4 prescribes; the commit message notes the revision (`Revise envelope bundle <bundle-id> to v<N+1>`).

## Exit

Print the Step 5 exit one-liner. Required outputs: bundle path, new version, supersedes hash, delta summary, verdicts for changed/new envelopes, validator result, checkpoint and commit status, per-slice run commands.

## Tripwires

- Hash the prior `bundle.json` BEFORE any rewrite; a bumped version without a valid `supersedes` fails validation (version ≥ 2 requires a 64-hex hash).
- Only changed/new envelopes get verdicts; never silently alter a carried-forward envelope.
- Fail-closed: a failed validation or zero-approved delta leaves the prior bundle as the live version.
