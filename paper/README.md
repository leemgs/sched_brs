# Paper: Practical Bounded Responsiveness Scheduling for Low-Latency Mobile Systems

LaTeX sources and the compiled PDF for the paper accepted to the
**IEEE Transactions on Mobile Computing (TMC)**, 2026
(manuscript ID: **TMC-2026-01-0047**).

## Contents

| File / pattern            | Description                                                        |
| ------------------------- | ----------------------------------------------------------------- |
| `main.tex`                | Master document; `\input`s the section files below.               |
| `main.pdf`                | Compiled camera-ready paper (built from `main.tex`).              |
| `001-title.tex`, `003-author.tex`, `005-abstract.tex` | Title, author block, and abstract.    |
| `010-introduction.tex` … `100-conclusion.tex`          | Body sections in reading order.       |
| `095_reference.tex`, `099_bib.tex`                     | Bibliography inclusion glue.          |
| `reference-data.bib`      | BibTeX bibliography database.                                      |
| `IEEEtran.cls`, `IEEEtranDOI.bst` | IEEE journal class and DOI-aware bibliography style.       |
| `fig_*.png`, `fig0_author-lim2.png`               | Figures (architecture, evaluation, author photo).     |
| `latexmkrc`               | `latexmk` configuration (sets the build time zone).               |

## Building

Requires a TeX distribution (TeX Live) with `latexmk`, `pdflatex`, and
`bibtex`.

```bash
cd paper
latexmk -pdf main.tex     # produces main.pdf
latexmk -c                # remove build intermediates (keeps main.pdf)
```

Build intermediates (`*.aux`, `*.bbl`, `*.log`, …) are ignored via
`.gitignore`; `main.pdf` is the tracked deliverable.

## Citation

See the `## Citation` section in [`../code/README.md`](../code/README.md)
for the IEEE-style reference and BibTeX entry.
