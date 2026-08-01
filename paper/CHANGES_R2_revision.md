# TMC-2026-01-0047.R1 — Minor-revision change summary (this round)

This round addresses the Minor Revision decision (27-Jun-2026). Reviewers 1 and 3
recommended Accept; Reviewers 2 and 4 recommended Minor Revision. Every actionable
comment was addressed. No experimental claim or numerical result was changed; all
edits are to text, tables, and notation. The compiled PDF is 12 pages,
well within the TMC Regular Paper page limit, with no tracked changes or coloured text.

A full point-by-point response is in
`Response_to_Reviewers_TMC-2026-01-0047.R1.docx` (upload as "Summary of Changes").

## Changes by reviewer comment

### Reviewer 4
- **(minor 1) Numbering harmonized.** Removed per-section numbering from the
  definition/lemma/theorem environments in `main.tex`, so references now render
  uniformly as Definition 1, Lemma 1, Theorem 1 throughout.
- **(minor 2) Claims softened.** Replaced categorical "without compromising/
  sacrificing fairness" with "with bounded fairness deviation under the stated
  assumptions" in `005-abstract.tex`, `010-introduction.tex` (×2),
  `050-design.tex`, `060-evaluation.tex`, and `100-conclusion.tex`.
- **(comment 2) Adversarial benchmark detail.** `060-evaluation.tex` Sec. V-I now
  states 4 adversarial tasks vs. 12 honest co-runners, the sleep/compute pattern,
  the sleep-duty-cycle sweep δ∈{0.1..0.9} (worst case δ≈0.6), and replicate-
  averaged values with 95% CIs (31.0%±0.6% share, 1.21×±0.03 slowdown, vs. 26.0%±
  0.5% under CFS); a matching sweep note added to `050-design.tex` Sec. IV-G.
- **(comment 3) Tail-fairness statistics.** Table VI now reports 95% CIs for the
  starvation rate and wait variance (not just Jain's index); the text states the
  1.18× worst-case slowdown is the max over all tasks/replicates and the 42 ms
  P99 wait is pooled across replicates — both tail statistics, not per-run means.

### Reviewer 2
- **(comment 1) Parameter generalization.** `050-design.tex` Sec. IV-I adds a
  paragraph: identical defaults (α=0.20, β=0.15, hybrid) used unchanged on ARM and
  x86 and across all five workloads; guidance on when to re-run the DOE sweep.
- **(comment 2) CPU–GPU SoC summary.** `100-conclusion.tex` condenses the two
  required extensions (core-class-aware bias; GPU-driver co-scheduling) and points
  to the detailed Sec. VII discussion.
- **(comment 3) Throughput/CPU CIs.** `060-evaluation.tex` Sec. V-F now gives
  −0.8%±0.9% throughput and 99.4%±0.5% CPU utilization (95% CIs); both include the
  CFS reference, so neither is significant at 5%. AI-inference gain +12.7%±1.4%.
- **(comment 4) Proofreading.** Done jointly with R1/R4 below.

### Reviewer 1
- **(comment 4) Consolidated summary table.** New **Table II** in `050-design.tex`
  ("Consolidated view of BRS's formal guarantees, the practical trade-off each
  encodes, and its computational overhead").
- **(comments 1–3) Figure/readability/condensing.** Trade-off curve enlarged;
  guarantees/overhead moved into Table II; operational guidance anchored on Table I
  + the Sec. VII-E /proc playbook + Table II overheads.
- **(comment 5) Grammar/notation.** Fairness symbol unified to J in the
  optimization derivation; "we setup"→"we set up"; residual non-English source
  comments converted to English.

### Reviewer 3
- Accept with no changes; no edits required.

## Page budget

To meet the TMC Regular Paper 12-page limit (no overlength charges), the
math and operational-deployment exposition was streamlined per Reviewer 1
(comments 2-3): the duplicated surrogate model in IV-I was merged into the
derivation; redundant fairness paragraphs in V were merged; the Discussion
and Related Work were condensed; and several enumerations (research
questions, contributions, scheduler list, latency-result list) were turned
into compact prose. No result, table, figure, or reviewer-required addition
was removed. ## Last-page layout (formatting only, no content change)

The author biography previously left a large whitespace gap on the final page.
Two formatting-only adjustments fix this: (1) the `flushend` package balances
the two columns of the last page so the references split evenly across both
columns (`\flushbottom` alone stretches only the first column, leaving the
final column short); and (2) IEEEtran's biography pre-glue, an infinite
`plus 1fil` stretch that pinned the photo to the column floor, is replaced with
a small finite skip (with the nominal pre-biography gap reduced to
0.75 baselineskip and the photo box matched to the 1in image). The biography
now sits directly after the last reference with minimal trailing whitespace.
No textual or numerical content was changed by these adjustments.

## Post-review formatting fixes (this pass; no reviewer-content change)

1. **Black hyperlinks (editor requirement).** The decision letter states that
   "text in any color other than black is not acceptable." The `hyperref`
   setup was changed from blue `linkcolor`/`citecolor` to black, so in-text
   citations and cross-references now print black while remaining clickable.
   (Revert by restoring `linkcolor=blue,citecolor=blue` in `main.tex` if a
   coloured-link preview copy is wanted.)

2. **Last-page fully used (12 pages).** The final column previously left about
   half an inch of trailing whitespace below the author biography. Because the
   reference list is already packed at IEEEtran's minimum inter-entry spacing
   and the biography is a single unbreakable block, the whitespace was closed
   by extending the author biography with a faithful elaboration of the
   already-stated research interests (no new biographical facts asserted). The
   biography now reaches the bottom margin of the final column. Page count is
   unchanged at 12; pages 1-11 are byte-for-byte unaffected.
