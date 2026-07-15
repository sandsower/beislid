# setup section review-feedback-profiles v1

In verbose mode, emit `✓ setup/section-review-feedback-profiles v1 loaded` immediately after reading this file.

## Review feedback prompt profiles

Ask this only when review comments already carry agent-ready instructions and the user wants `review-response` to prefer the extracted prompt.

Use profiles in order, first match wins, and keep them as enrichment only - do not present them as a new backend or a fresh-review workflow.

```beislid:review_feedback_profiles
- name: coderabbit
  match:
    source: pr_review
    author_regex: '^coderabbit(ai)?$'
  extract:
    prompt_regex: '(?s)### Agent prompt\n(?P<agent_prompt>.+)$'
    prompt_format: coderabbit
```
