# Beislið — animation frame set

Canonical mark: `beislid-mark.svg` / `beislid-mark-dark.svg`
(identical to the NE frame `03c-only-ne.svg`)

## Frames

8 frames at s3 #249081 (locked saturation), one accented spoke per frame, clockwise from the top:

| # | Direction | Light                  | Dark                       |
|---|-----------|------------------------|----------------------------|
| 0 | N (top)   | `03c-only-n.svg`       | `03c-only-n-dark.svg`      |
| 1 | NE *(canonical)* | `03c-only-ne.svg` | `03c-only-ne-dark.svg`     |
| 2 | E         | `03c-only-e.svg`       | `03c-only-e-dark.svg`      |
| 3 | SE        | `03c-only-se.svg`      | `03c-only-se-dark.svg`     |
| 4 | S         | `03c-only-s.svg`       | `03c-only-s-dark.svg`      |
| 5 | SW        | `03c-only-sw.svg`      | `03c-only-sw-dark.svg`     |
| 6 | W         | `03c-only-w.svg`       | `03c-only-w-dark.svg`      |
| 7 | NW        | `03c-only-nw.svg`      | `03c-only-nw-dark.svg`     |

To regenerate (e.g. at a different saturation), edit `generate_matrix.py` and run `python3 generate_matrix.py`.
