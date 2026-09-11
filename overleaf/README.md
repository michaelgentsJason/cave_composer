# CAVERN paper workspace

**Latest source and PDF:** [compiled snapshot](main.pdf) and
[clean-clone reproduction](../reproducibility/README.md). The current manuscript
has nine pages, including the hard-cave showcase; result placeholders remain.
The build uses the included figure PDFs without silently regenerating them.
Use `--render-schematics` to explicitly redraw the two schematic overviews.
The [ready-to-import Overleaf ZIP](cave_composer_overleaf.zip) was compiled after
extraction into a separate directory; it includes all figures used by the paper.

This is an anonymous **working draft**, not a submission-ready manuscript.
Cave Composer remains the generator and public code/API name. CAVERN denotes
the paper: *Controllable and Validated Environments for Robotic Navigation in
Underwater Caves*. The acronym expands to *Controllable And Validated
Environments for Robotic Navigation*.

The single paper fact ledger is [CLAIM_EVIDENCE.yaml](CLAIM_EVIDENCE.yaml).
Use [PAPER_PLAN.md](PAPER_PLAN.md) for narrative and experiment priorities,
[FIGURE_PLAN.md](FIGURE_PLAN.md) for figures, and [COMPLIANCE.md](COMPLIANCE.md)
for official-template provenance and unresolved submission requirements.
The [training interface](../research_workspace/README.md) is an offline review
handoff; it does not establish Isaac runtime or policy performance.

## Local build

From the repository root (Windows Python environment shown):

```powershell
.venv/Scripts/python.exe scripts/build_cavern_paper.py
.venv/Scripts/python.exe scripts/check_cavern_paper.py
.venv/Scripts/python.exe scripts/check_cavern_paper.py --submission
```

Requires pdfLaTeX, BibTeX, Poppler (`pdfinfo`, `pdffonts`, `pdftotext`) and the
repository Python dependencies including Matplotlib/PyYAML. Build outputs and
individual command logs are in `build/`. The final command is expected to
return nonzero while result placeholders and human decisions remain unresolved.
That is separate from a successful draft build. Static checks do not replace
author review or establish the truth of numerical claims.

## Overleaf import

```powershell
.venv/Scripts/python.exe scripts/package_cavern_overleaf.py --output outputs/cavern_paper_v01/overleaf_draft.zip
```

Use a new output filename for each immutable package. In your private Overleaf
account choose **New Project → Upload Project**, import the ZIP, select
`main.tex` and pdfLaTeX, then compile. No account operation or upload is performed
by these scripts. The ZIP includes official class/style files, cited bibliography,
sections, tables, and editable/vector figures. It excludes local evidence paths,
source acquisition identities, downloads, logs and author-approval files.
Maintain those in the repository; Overleaf edits must later be reconciled with
the canonical claim ledger before interpreting or submitting results.

Figure source is [render_figures.py](figures/src/render_figures.py).
SVG retains editable text; PDF is vector and PNG is 300 dpi. The two diagrams
are structure drafts, not experimental visualizations or platform screenshots.

No result cells have been filled with invented values. The method text reports
only version-specific geometric evidence. Eight pages is the total maximum,
including references and acknowledgment; do not pad the draft to eight pages.
