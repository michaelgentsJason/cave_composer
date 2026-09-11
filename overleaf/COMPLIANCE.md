# ICRA 2027 compliance record

Verified from the [official call](https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/)
and [PaperCept LaTeX support](https://ras.papercept.net/conferences/support/tex.php)
on 2026-09-10. The originals were actually downloaded, not replaced with
unverified local templates. See [template_original/provenance.json](template_original/provenance.json)
for resolved URLs, UTC download times, sizes and SHA256 values.

Official requirements recorded for this draft: at most eight pages **in total**,
double-anonymous review, and no extra textual supplement beyond that limit.
The call lists September 15, 2026, 23:59 PST as the paper deadline; confirm the
submission portal's time convention before submission. Optional video has its
own window and limits (20 MB, three minutes, at least 480 lines and 20 fps).
The call requires disclosure of AI-generated text, figures or code, including
the tool and affected portions. Authors retain responsibility. Use plain text
URLs rather than embedded active links in the submitted PDF. Recheck the live
policy immediately before submission because these rules can change.

## Template and layout

- Unmodified `ieeeconf.cls` from the official `ieeeconf.zip`; the class's old
  internal revision date is not a claim that the conference template was
  newly authored in 2027. `IEEEtran.bst` comes from the official BST archive.
- Official letterpaper, 10 pt, conference configuration and the template's
  `\overrideIEEEmargins`; no custom margins, font-size compression or line-spacing
  reduction. All figures, references and acknowledgment count toward eight pages.
- `build/paper_check.json`, `pdfinfo.txt`, `pdffonts.txt`, and `main.log` record
  page, embedded-font, citation and overflow checks. Render and inspect every page.

## Unresolved human decisions

`research_workspace/submission_approvals.json` starts with every decision false.
Only the authors should confirm author identities/order, permission to publish
source-derived assets, repository licensing, technical content, anonymity,
AI disclosure, claim-to-evidence alignment and final submission authorization.
No license has been selected on their behalf.

The draft author block is anonymous and PDF author metadata is empty. Private
source names and personal repository links are excluded from the draft ZIP.
The local provenance ledger and downloads are **not anonymous submission files**.
Inspect figure/SVG metadata, self-citation context, public searchability of names,
and any later screenshots manually. A token scan is only a partial check.

## AI-use inventory

OpenAI Codex assisted with all initial manuscript section drafts, workspace
utilities and Matplotlib figure source in this round. ARIS paper-write and
paper-compile workflows guide writing/build checks; ARIS requires an independent
GPT-5.5 draft review. Figures use the local figures4papers
`scientific-figure-making` skill. No AI-generated experimental screenshot,
learning curve or policy outcome is included. Human authors must review and
finalize the acknowledgment disclosure before submission.
