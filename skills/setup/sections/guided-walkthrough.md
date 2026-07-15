# setup section guided-walkthrough v1

In verbose mode, emit `✓ setup/section-guided-walkthrough v1 loaded` immediately after reading this file.

## Guided walkthrough thresholds

Configure `guided_walkthrough.threshold_files` and `guided_walkthrough.threshold_lines` only when the user wants to override the defaults of 5 files and 200 lines.
Ask for one positive integer at a time.
Explain that exceeding either threshold offers an interactive walkthrough before review.
Remove both keys to restore defaults, and never create duplicates.
