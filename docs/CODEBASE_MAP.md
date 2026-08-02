# ShieldRouter Codebase Map

This map describes the final repository layout and ownership boundaries without
changing the implementation structure.

## Main Directories

| Path | Purpose | Included in code.zip |
|---|---|---|
| `code/` | Runnable ShieldRouter application, tests, prompts, and evaluation evidence. | Yes |
| `code/src/shieldrouter/` | Production routing package. | Yes |
| `code/tests/` | Unit and integration tests for schema, retrieval, media, safety, resolver, CLI, and determinism. | Yes |
| `code/prompts/` | Optional OpenRouter advisory prompts. The selected final mode does not require them. | Yes |
| `code/evaluation/` | Final baselines, audit reports, diagnostics, sample evaluation, and AI Judge evidence. | Yes |
| `docs/` | Architecture and implementation-ready design documents. | Yes |
| `dataset/` | Participant-facing local CSVs and media used to generate predictions. | No |
| `submission/` | Final upload artifacts. This directory is intentionally untracked. | No |
| `.tmp/`, `.venv/`, caches | Temporary validation, environments, extraction folders, and model/runtime caches. | No |

## Production Modules

| Module | Responsibility |
|---|---|
| `main.py` | CLI commands: validate input, run router, validate output, prepare models, trace, smoke-test provider, evaluate sample, and write summary JSON. |
| `schemas.py` | Dataset headers, official output columns, allowed enums, and trace dataclasses. |
| `io.py` | CSV I/O, dataset schema validation, parsing helpers, unique-key validation, and media path containment. |
| `indexes.py` | In-memory indexes over users, groups, memberships, businesses, history, events, images, and voice notes. |
| `normalize.py` | Text normalization, tokenization, URL/domain extraction, and ASR spelling normalization used by retrieval and safety. |
| `retrieval.py` | Same-user TF-IDF-style evidence scoring with stable math, quantized comparisons, and deterministic tie-breaking. |
| `behaviorgraph.py` | Trust, affinity, fatigue, forwarding fatigue, novelty, transaction relationship, quiet hours, load, group mute, direct mention, repetition, and missing-context features. |
| `safety_rules.py` | Deterministic safety gate for credentials, OTP/PIN/password requests, QR/payment pressure, suspicious domains, prompt injection, forwarding chains, and unverified financial senders. |
| `media.py` | Media path resolution, media extraction orchestration, voice transcript metadata, failure handling, and prompt-injection treatment. |
| `local_image.py` | Local image decoding, OCR, QR detection, visible text, URLs/domains, prices, dates, visual risk signals, cache versioning, and sanitised errors. |
| `provider.py` | Offline, local voice, local multimodal, and optional OpenRouter providers; request caps, retries, cache keys, transcriber, and provider stats. |
| `online_ai.py` | Restricted payload construction, optional advisory merging, and schema validation for model outputs. |
| `fallback_synthesis.py` | Deterministic synthesis of urgency, direct mention, message type, preliminary action, ambiguity, and grounded facts. |
| `exception_check.py` | Muted-group and quiet-hours exception eligibility for trusted critical direct mentions. |
| `resolver.py` | Final action owner; applies safety overrides, exception handling, quiet/load downgrades, fatigue, forwarding, suspicious digest, ambiguity, and safe digest policy. |
| `confidence.py` | Bounded deterministic confidence calibration with ambiguity, media failure, missing-context, evidence, safety, and feature adjustments. |
| `reason.py` | Short grounded reason construction from resolver rule, safety, features, synthesis, and selected evidence. |
| `consistency.py` | Reason/action/evidence consistency checks and conservative repair. |
| `ai_models.py` | Strict Pydantic models for local image facts, media facts, advisory output, safety payloads, and synthesis payloads. |
| `validate.py` | Official output validation: exact schema, row coverage, unique IDs, allowed enums, confidence bounds, and same-user evidence. |

## Test Organization

| Area | Representative tests |
|---|---|
| Dataset and output schema | `test_io.py`, `test_output.py`, `test_schemas.py` |
| BehaviorGraph and personalization | `test_behaviorgraph.py`, `test_exception_check.py` |
| Safety and resolver precedence | `test_safety_rules.py`, `test_resolver.py`, `test_consistency.py` |
| Retrieval and reproducibility | `test_retrieval.py` |
| Local image and multimodal behavior | `test_local_image.py`, `test_openrouter_media_voice.py` |
| Voice metadata and model preparation | `test_voice_metadata.py`, `test_cli_local_voice.py` |
| Provider cache, retry, and caps | `test_provider_cache.py`, `test_online_ai.py` |
| Summary and artifact safety | `test_summary_json.py`, `test_prompts.py` |

## Runtime Data Flow

1. `main.py` loads the participant dataset with `io.load_routing_dataset`.
2. `indexes.build_indexes` constructs lookup tables scoped to participant data.
3. `media.extract_media` resolves image or voice media through contained paths.
4. `local_image.LocalImageExtractor` and `provider.LocalWhisperTranscriber` add local OCR/ASR facts in selected local multimodal mode.
5. `safety_rules.assess_safety` runs deterministic safety checks on text plus trusted local media text.
6. `retrieval.retrieve_evidence` selects same-user historical evidence.
7. `behaviorgraph.build_features` builds personalization features.
8. `fallback_synthesis.synthesize` creates deterministic urgency/type/action context.
9. `exception_check.check_exception` evaluates muted-group and quiet-hour exceptions.
10. `resolver.resolve` owns the final action and message type.
11. `confidence.calibrate_confidence` and `reason.build_reason` produce final explanation fields.
12. `consistency.validate_and_repair_reason` repairs unsupported reason claims.
13. `validate.validate_output_rows` checks the final rows before write.

## Evaluation Areas

- Final candidate: `code/evaluation/baselines/final_design_aligned.csv`
- Final summary: `code/evaluation/final_design_aligned_summary.json`
- Reason consistency: `code/evaluation/FINAL_REASON_CONSISTENCY_REPORT.csv`
- Evidence audit: `code/evaluation/final_evidence_audit.csv`
- Threshold audit: `code/evaluation/FINAL_EVIDENCE_THRESHOLD_AUDIT.csv`
- Reproducibility diagnostic: `code/evaluation/MSG_082_REPRODUCIBILITY_DIAGNOSTIC.csv`
- Test coverage matrix: `code/evaluation/FINAL_TEST_COVERAGE_MATRIX.md`
- AI Judge brief: `code/evaluation/AI_JUDGE_BRIEF.md`

## Submission Boundary

The ZIP contains runnable code, prompts, tests, evaluation evidence, and final
docs. It excludes `dataset/`, media files, `.git/`, `AGENTS.md`, `.env`,
virtual environments, `.tmp/`, caches, model files, transcript logs, previous
ZIP files, and `submission/`.

The three protected upload files are:

- `submission/code.zip`
- `submission/output.csv`
- `submission/chat_transcript.txt`
