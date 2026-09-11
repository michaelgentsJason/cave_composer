# Citation audit

`verification.json` records primary arXiv page metadata for each cited work,
its cached source SHA256, query URL and verification time. The corresponding
HTML files are original local verification records; they are not part of the
anonymous Overleaf import package.

`scripts/fetch_cavern_references.py` extracts authors, title and year from
actual citation meta fields. It does not guess publication venues. NVIDIA's
corporate author is protected in BibTeX; the colon used as a metadata separator
is not treated as an author. Full author lists remain in `verification.json`;
long lists are abbreviated with BibTeX's standard `and others` in the paper.

| Citation | Primary source verified | Supported use |
|---|---|---|
| PLUME | https://arxiv.org/abs/2508.20926 | procedural underground environments; no superiority claim |
| Domain Randomization | https://arxiv.org/abs/1703.06907 | visual variation for transfer in that study; not evidence for our navigation gains |
| Isaac Lab | https://arxiv.org/abs/2511.04831 | framework relationship to Isaac Sim; not colleague runtime proof |
| FlashSAC | https://arxiv.org/abs/2604.04539 | existing baseline, not our algorithm |
| PPO | https://arxiv.org/abs/1707.06347 | existing optimization method; recurrence/vision requires implementation details |

After independent draft review, Tobin et al. was upgraded to its IROS 2017
record using actual CrossRef BibTeX and the IEEE publisher page. FlashSAC was
upgraded to the official RSS 2026 proceedings BibTeX. The original published
records and hashes are in `published_verification.json`; other entries remain
explicit preprint citations. The RSS author order/spelling differs from arXiv;
the paper follows the cited proceedings. A malformed page-range character in
CrossRef's BibTeX was normalized to `23--30`. DBLP returned an HTML challenge,
so that response was not treated as bibliographic evidence or retained.
Related-work coverage remains an explicit paper TODO.
The PPO paper does not establish a particular recurrent visual implementation.
