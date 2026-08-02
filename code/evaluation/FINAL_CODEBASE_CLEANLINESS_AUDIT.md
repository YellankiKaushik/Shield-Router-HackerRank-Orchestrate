# Final Codebase Cleanliness Audit

Audit timestamp: 2026-08-02T15:40:08+05:30

Classification values: BLOCKING, SAFE_TO_FIX_NOW, POST_SUBMISSION_REFACTOR,
ACCEPTABLE_TECHNICAL_DEBT, FALSE_POSITIVE.

## Summary

No blocking repository-cleanliness defect was found. The implementation is
organized around a small production package, explicit CLI entry points, and a
focused test suite. The only safe pre-submission project cleanup identified was
documentation/navigation: the root README still read like a starter README and
did not direct reviewers to the final code package, architecture docs, final
reports, AI Judge brief, setup, model preparation, security model, and
limitations.

## Findings

| ID | Area | Classification | Finding | Risk | Exact file | Expected behavior impact | Test required | Action |
|---|---|---|---|---|---|---|---|---|
| CQA-001 | README navigation | SAFE_TO_FIX_NOW | Root README was starter-oriented and did not clearly point reviewers to final ShieldRouter docs, setup, evaluation, AI Judge brief, output contract, security model, and limitations. | Reviewer confusion, not runtime behavior. | `README.md` | None. Documentation only. | pytest, input/output validation, output hash check, ZIP validation if packaged. | Fixed in this audit. |
| CQA-002 | Repository map | SAFE_TO_FIX_NOW | No concise codebase map existed for reviewers. | Lower interview/readability quality, not runtime behavior. | `docs/CODEBASE_MAP.md` | None. Documentation only. | pytest, validation, ZIP validation if packaged. | Added in this audit. |
| CQA-003 | Historical evaluation baselines | ACCEPTABLE_TECHNICAL_DEBT | Several tracked baseline CSVs remain under `code/evaluation/baselines/`. | Some clutter, but they are useful audit/interview evidence and are included intentionally. | `code/evaluation/baselines/*` | None. | Existing tests and ZIP size check. | Keep before submission. |
| CQA-004 | Older unified-design pseudocode | ACCEPTABLE_TECHNICAL_DEBT | `docs/shieldrouter_tech_design.md` contains older illustrative examples with `risk_flags`, `user_id`, and `scam_or_risk`. | Could confuse a reader unless they observe source-of-truth priority. | `docs/shieldrouter_tech_design.md` | None. | Schema tests. | Keep; final implementation doc and audit mark these as superseded by official schema. |
| CQA-005 | Duplicate regex concepts | POST_SUBMISSION_REFACTOR | Safety and image modules intentionally duplicate related regex concepts for text and OCR contexts. | Maintenance drift over time. | `safety_rules.py`, `local_image.py`, `media.py` | Refactor could alter routing; not safe near deadline. | Full suite plus output hash review. | Defer. |
| CQA-006 | Large CLI module | POST_SUBMISSION_REFACTOR | `code/main.py` owns many CLI commands and summary helpers. | Readability only; current behavior is tested. | `code/main.py` | Refactor could affect commands. | Full suite and clean-room. | Defer. |
| CQA-007 | Broad row/provider exception boundaries | ACCEPTABLE_TECHNICAL_DEBT | Row and provider failures are caught broadly in boundary layers. | Could hide internal error classes, but preserves required output rows. | `orchestrator.py`, `media.py`, `provider.py`, `local_image.py` | Current behavior desired for hackathon robustness. | Existing failure-injection tests. | Keep. |
| CQA-008 | Default cache path under `code/` | ACCEPTABLE_TECHNICAL_DEBT | Default runtime cache is `code/.shieldrouter_cache`, excluded from packaging. | User must avoid committing cache; already excluded and scanned. | `main.py` | None for validated runs. | Packaging/security scan. | Keep; use explicit temp cache in audits. |
| CQA-009 | No static type/ruff gate | POST_SUBMISSION_REFACTOR | The repo uses pytest but no ruff/mypy/pyproject enforcement. | Style/type regressions possible later. | Repository config | Adding tools now risks dependency churn. | New CI. | Defer. |
| CQA-010 | Message-ID literals in tests/docs | FALSE_POSITIVE | `msg_` and `message_` strings appear in tests and design examples. | None; production search showed no message-ID-specific routing branch. | `code/tests/*`, `docs/*` | None. | Retrieval determinism tests. | No fix. |
| CQA-011 | Prompt docs mention unofficial enum in rejection tests | FALSE_POSITIVE | Tests include `scam_or_risk` to prove invalid model output is rejected. | None; reinforces official schema. | `test_prompts.py` | None. | `test_synthesis_output_rejects_non_official_enum` | No fix. |
| CQA-012 | Submission manifest stale note | SAFE_TO_FIX_NOW | An untracked manifest note from the previous packaging audit said the final docs/artifact commit was not approved, although commit `3632380` exists. | Submission metadata confusion, not runtime behavior. | `submission/SUBMISSION_MANIFEST.txt` | None; submission artifact only. | Hash/security scan. | Already fixed in prior audit; not committed. |

## Inspected Areas

- Directory organization: clear `code/`, `docs/`, `dataset/`, `submission/`, `.tmp/`, and `.venv/` boundaries.
- Package boundaries: production code is in `code/src/shieldrouter/`; CLI is in `code/main.py`.
- Module responsibilities: loader, indexes, media, image, provider, safety, behavior, retrieval, resolver, confidence, reason, consistency, and validation are separated.
- Dead code/unused imports: no blocking dead production code found from targeted inspection.
- Duplicate helpers/constants/regexes: acceptable now, defer centralization.
- Temporary diagnostics: final diagnostics under `code/evaluation/` are intentional evidence; `.tmp/` remains untracked and excluded.
- Debug prints: production CLI prints user-facing summaries and errors; no blocking debug output found.
- Hardcoded absolute paths: none found in code/ZIP runtime configuration.
- Dataset coupling: code reads official participant dataset schemas; no organizer-only coupling found.
- Message-ID-specific logic: none found in production code.
- Terminology: final docs and code use official output enums; older design examples are superseded.
- Type hints: generally present; no blocking gap.
- Broad exception handling: limited to row/media/provider boundaries and tested.
- Hidden side effects: cache writes are explicit under cache dirs; output write validates rows first.
- Encoding/line endings: CSV writer uses UTF-8 and `\n`; docs are UTF-8.
- README navigation: fixed.
- Generated artifact segregation: `submission/` untracked; `.tmp/` untracked; evaluation evidence tracked intentionally.
- Packaging exclusions and secret hygiene: validated in previous final packaging and repeated in this audit after rebuild.

## Deferred Refactors

- Consolidate duplicate regex vocabularies across text safety and OCR safety.
- Split `code/main.py` into smaller command modules.
- Add optional ruff/mypy configuration after submission.
- Add automated generation for final audit/report files.
- Add a richer local vision model only if future rules allow model size/time.
