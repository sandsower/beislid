# setup section pr-description-formatter v1

In verbose mode, emit `✓ setup/section-pr-description-formatter v1 loaded` immediately after reading this file.

## PR description formatter

Configure `pr_description.formatter_skill` only when an installed formatter skill should process drafted PR descriptions.
Ask for the skill name and optional `pr_description.formatter_args` map.
Explain that ready-for-review still shows the formatted draft at its normal approval boundary.
Never create duplicate keys; update or remove the existing formatter configuration.
