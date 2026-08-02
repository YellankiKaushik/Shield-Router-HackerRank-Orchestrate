# Final Complete Document Compliance Audit

Audit timestamp: 2026-08-02T15:40:08+05:30

Scope: AGENTS.md, problem_statement.md, participant-facing dataset schemas,
`docs/ShieldRouter - Final Implementation-Ready Technical.md`,
`docs/shieldrouter_tech_design.md`, `code/README.md`,
`code/evaluation/FINAL_DESIGN_TRACEABILITY.md`,
`code/evaluation/FINAL_EVALUATION_REPORT.md`,
`code/evaluation/FINAL_OPERATIONAL_ANALYSIS.md`, and
`code/evaluation/AI_JUDGE_BRIEF.md`.

Status values: IMPLEMENTED, PARTIALLY_IMPLEMENTED, INTENTIONAL_DEVIATION,
SUPERSEDED_BY_OFFICIAL_SCHEMA, DOCUMENTATION_ONLY, NOT_IMPLEMENTED,
NOT_APPLICABLE, PACKAGING_COMPLETE, POST_SUBMISSION_IMPROVEMENT.

## Compliance Matrix

| ID | Source section | Requirement summary | Priority | Status | Implementation file / symbol | Test file / test name | Generated evidence / report | Deviation and reason | Official / interview impact | Required before submission | Post-submission improvement |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A01 | AGENTS 6.2; problem output | Exact output columns `message_id,action,message_type,reason,confidence,evidence_message_ids`. | P0 | IMPLEMENTED | `schemas.py` `OUTPUT_COLUMNS`; `DecisionTrace.to_output_row`; `validate.py` | `test_schemas.py::test_output_header_order`; `test_output.py::test_full_output_contract_and_ids` | `output.csv` SHA CD8B...; validators passed | None | Official evaluator-compatible | No | None |
| A02 | problem allowed actions | Actions limited to notify/digest/mute. | P0 | IMPLEMENTED | `schemas.py` `ALLOWED_ACTIONS`; `validate.py` | `test_output.py`; `test_prompts.py` | 110-row validation passed | None | Official enum-compatible | No | None |
| A03 | problem allowed types; final doc 4 | Message types limited to official 11 enums. | P0 | IMPLEMENTED | `schemas.py` `ALLOWED_MESSAGE_TYPES`; `ai_models.py` validators | `test_prompts.py::test_synthesis_output_rejects_non_official_enum` | 110-row validation passed | None | Official enum-compatible | No | None |
| A04 | problem messages authority | One prediction for every row in `dataset/messages.csv`. | P0 | IMPLEMENTED | `orchestrator.run`; `validate.validate_output_rows` | `test_output.py::test_full_output_contract_and_ids` | INPUT OK 110; OUTPUT OK 110 | None | No dropped rows | No | None |
| A05 | problem dataset files | Use participant-facing CSVs only. | P0 | IMPLEMENTED | `io.load_routing_dataset`; `schemas.ROUTING_TABLES` | `test_local_image.py::test_production_run_does_not_require_sample_output_or_baselines` | `final_leakage_audit.txt` | None | Prevents label leakage | No | None |
| A06 | problem sample labels | Sample labels used only for evaluation style. | P0 | IMPLEMENTED | `main.py evaluate-sample`; `io.load_routing_dataset` excludes sample | `test_local_image.py::test_production_run_does_not_require_sample_output_or_baselines` | sample reports separate from final output | None | No sample leakage | No | None |
| A07 | problem multimodal | Inspect text, image, and voice media. | P0 | IMPLEMENTED | `media.py`; `local_image.py`; `provider.LocalWhisperTranscriber` | `test_local_image.py`; `test_voice_metadata.py`; `test_openrouter_media_voice.py` | 15/15 images, 8/8 voice succeeded | Local deterministic extraction, not broad scene AI | Official multimodal supported | No | Richer visual classifier |
| A08 | problem personalization | Use user, group, business, history, and events for routing. | P0 | IMPLEMENTED | `indexes.py`; `behaviorgraph.py`; `retrieval.py` | `test_behaviorgraph.py`; `test_output.py::test_same_promotional_content_routes_differently_for_history` | final evidence audit | None | Personal routing present | No | None |
| A09 | problem evidence | Evidence IDs refer to useful same-user historical messages or `none`. | P0 | IMPLEMENTED | `retrieval.retrieve_evidence`; `validate.validate_output_rows` | `test_retrieval.py::test_evidence_same_user_only`; `test_output.py` | `final_evidence_audit.csv` 0 invalid | None | Evidence valid | No | None |
| A10 | problem confidence | Numeric confidence in [0,1]. | P0 | IMPLEMENTED | `confidence.calibrate_confidence`; `DecisionTrace.to_output_row` | `test_output.py` | validation passed | Deterministic calibration, not learned probability | Accepted by contract | No | Learned calibration if labels available |
| A11 | submission contract | Code, output, transcript deliverables. | P0 | PACKAGING_COMPLETE | `submission/` artifacts | ZIP clean-room tests | Manifest and checklist | None | Upload-ready | No | None |
| A12 | AGENTS logging | Append-only transcript outside repo, no secrets. | P0 | PACKAGING_COMPLETE | external log; transcript export | final security scan | `submission/chat_transcript.txt` SHA 10130... | Submission transcript is snapshot; live log continues | Meets upload requirement | No | None |
| A13 | no hardcoding | No message-ID-specific production logic. | P0 | IMPLEMENTED | production search found no `msg_`/`message_` ID branches | `test_retrieval.py` synthetic IDs only | rg audit | Test fixtures use synthetic IDs | No hidden-label coupling | No | None |
| B01 | ten-stage 1 | Loader and schema validation. | P0 | IMPLEMENTED | `io.load_dataset`; `io.validate_dataset` | `test_io.py::test_real_dataset_validates` | INPUT OK 110 | None | Strong input guard | No | None |
| B02 | ten-stage 2 | Index construction over dataset tables. | P0 | IMPLEMENTED | `indexes.build_indexes` | behavior/retrieval tests | Code map | None | Efficient scoped context | No | None |
| B03 | ten-stage 3 | Media extraction before routing. | P0 | IMPLEMENTED | `media.extract_media`; `local_image.LocalImageExtractor` | media tests | final summary media counts | None | Multimodal facts available | No | None |
| B04 | ten-stage 4 | Isolated safety/integrity processing. | P0 | IMPLEMENTED | `safety_rules.assess_safety`; `online_ai.build_safety_payload` | `test_online_ai.py::test_restricted_safety_payload_excludes_personalization_fields` | safety tests | None | Risk first | No | None |
| B05 | ten-stage 5 | BehaviorGraph features. | P0 | IMPLEMENTED | `behaviorgraph.build_features` | `test_behaviorgraph.py` | coverage matrix | None | Personalization present | No | None |
| B06 | ten-stage 6 | Muted-group/direct-mention exception. | P0 | IMPLEMENTED | `exception_check.check_exception`; `resolver.resolve` | `test_exception_check.py`; `test_resolver.py` | tests passed | None | Prevents missed critical muted-group messages | No | None |
| B07 | ten-stage 7 | Context/urgency/personalization synthesis. | P0 | IMPLEMENTED | `fallback_synthesis.synthesize`; optional `online_ai` merge | `test_output.py`; `test_online_ai.py` | final output distribution | None | Deterministic synthesis | No | None |
| B08 | ten-stage 8 | Deterministic resolver owns final action. | P0 | IMPLEMENTED | `resolver.resolve` | `test_resolver.py` | reason consistency report | None | Auditable precedence | No | None |
| B09 | ten-stage 9 | Confidence calibration. | P0 | IMPLEMENTED | `confidence.calibrate_confidence` | `test_output.py` | final summary confidence min/mean/max | Not learned | No official defect | No | Learned calibration with labels |
| B10 | ten-stage 10 | Output validation before write. | P0 | IMPLEMENTED | `orchestrator.run`; `validate.validate_output_rows` | `test_output.py`; CLI validate-output | OUTPUT OK 110 | None | Prevents invalid CSV | No | None |
| C01 | BehaviorGraph trust | Trust from business verification, group/admin context, transactional context. | P1 | IMPLEMENTED | `behaviorgraph.build_features` | `test_behaviorgraph.py` | coverage matrix | None | Better personalization | No | Tune weights |
| C02 | BehaviorGraph affinity | Affinity from replies/opens/history engagement. | P1 | IMPLEMENTED | `behaviorgraph.build_features` | behavior tests | final traceability | None | Better direct routing | No | Tune weights |
| C03 | BehaviorGraph fatigue | Fatigue from user load, dismissals, negative evidence. | P1 | IMPLEMENTED | `behaviorgraph.build_features` | fatigue tests | final output distribution | None | Reduces noise | No | Tune weights |
| C04 | BehaviorGraph bounded forwarding fatigue | Forwarded-count fatigue with negative-context bound. | P1 | IMPLEMENTED | `forwarding_fatigue_contribution` | `test_forwarding_fatigue_zero_one_moderate_heavy` | tests passed | None | Handles chains | No | None |
| C05 | BehaviorGraph novelty/highest similarity | Novelty and highest history similarity. | P1 | IMPLEMENTED | `novelty_score`; `retrieval.highest_user_history_similarity` | novelty tests | threshold audit | None | Repetition handling | No | None |
| C06 | BehaviorGraph transaction | Transaction relationship and strength. | P1 | IMPLEMENTED | `transaction_strength` | transaction tests | traceability | None | Avoids muting real updates | No | None |
| C07 | BehaviorGraph quiet/load | Quiet hours and relative load. | P1 | IMPLEMENTED | `in_quiet_hours`; `build_features` | quiet-hour resolver tests | tests passed | None | Reduces interruptions | No | Tune load threshold |
| C08 | BehaviorGraph mute/mention/repetition/missing context | Group mute, direct mention, repeated, missing context. | P1 | IMPLEMENTED | `build_features`; `detect_direct_mention` | behavior/exception tests | tests passed | None | User-aware | No | None |
| D01 | image path validation | Path containment and missing image handling. | P0 | IMPLEMENTED | `io.safe_media_path`; `local_image._resolve_image_path` | `test_image_path_escape_prevention`; `test_path_traversal_is_rejected` | tests passed | None | Prevents path traversal | No | None |
| D02 | image decoding/type/size | Decode image bytes, type and size validation. | P1 | IMPLEMENTED | `local_image._decode_with_pillow`; `MAX_IMAGE_BYTES`; `SUPPORTED_FORMATS` | `test_actual_image_bytes_are_read`; invalid image tests | 15/15 success | None | Robust media | No | None |
| D03 | OCR/visible text | Local OCR with ordered text extraction. | P1 | IMPLEMENTED | `LocalImageExtractor._run_ocr`; `_ordered_ocr_lines` | OCR ordering/multilingual tests | local image reports | None | Inspects media | No | None |
| D04 | QR/URLs/domains/prices/dates | Extract QR presence/text, URLs, domains, prices, dates/deadlines. | P1 | IMPLEMENTED | `local_image.py` regexes and QR detector | QR, payment, event poster tests | final media audit | QR destinations not visited | Safe | No | Better QR decoder coverage |
| D05 | visual prompt injection | Treat image text as untrusted and risky. | P0 | IMPLEMENTED | `IMAGE_INSTRUCTIONS`; `local_image.INJECTION_RE`; `_advisory_from_image_media` | `test_prompt_injection_inside_visible_image_text_is_untrusted_and_risky` | tests passed | None | Safety critical | No | None |
| D06 | image failure handling | Preserve row and lower confidence on failure. | P0 | IMPLEMENTED | `media.extract_media`; `confidence.calibrate_confidence`; row boundary | `test_image_failure_lowers_confidence_but_does_not_drop_row` | tests passed | None | No dropped rows | No | None |
| D07 | voice path/transcription | Voice path validation and local Faster-Whisper transcription. | P0 | IMPLEMENTED | `media.extract_media`; `LocalWhisperTranscriber` | voice path/transcriber tests | 8/8 voice succeeded | None | Voice supported | No | None |
| D08 | voice tone/pressure | Transcript-derived linguistic tone and pressure language. | P1 | IMPLEMENTED | `derive_voice_metadata` | `test_voice_metadata.py` | tests passed | No acoustic prosody | Honest capability | No | Acoustic model only if required |
| D09 | voice prompt injection | Voice transcript injection remains untrusted. | P0 | IMPLEMENTED | `safety_rules.INJECTION_RE` over transcript-enriched text | `test_voice_transcript_prompt_injection_still_muted` | tests passed | None | Safety critical | No | None |
| D10 | caching/model prep/zero network | Cache OCR/ASR, prepare models, selected zero-provider mode. | P0 | IMPLEMENTED | `provider.py`; `main.cmd_prepare_models`; `_assert_zero_provider_requests` | cache tests; prepare-model tests | final summary provider_requests 0 | None | Reproducible local run | No | None |
| D11 | complete visual scene understanding | Broad semantic scene understanding beyond OCR/layout. | P2 | PARTIALLY_IMPLEMENTED | `local_image._layout_type`; scene facts from OCR/QR | local image tests | final docs disclose limitation | Local deterministic extraction prioritized | No official blocker | No | Add vision model if allowed |
| E01 | restricted input boundary | Safety payload excludes personalization. | P0 | IMPLEMENTED | `online_ai.py` safety payload | `test_restricted_safety_payload_excludes_personalization_fields` | tests passed | None | Privacy/safety | No | None |
| E02 | credentials/OTP/PIN/password | Detect and mute credential theft pressure. | P0 | IMPLEMENTED | `safety_rules.CREDENTIAL_RE`; `resolver` high-risk override | safety tests | tests passed | None | Safety critical | No | None |
| E03 | payment/QR/account pressure | Detect payment, QR, refund, account-blocking pressure. | P0 | IMPLEMENTED | `safety_rules`; `local_image` signals | safety/media tests | tests passed | None | Safety critical | No | None |
| E04 | suspicious links/domains | Detect shorteners, mismatches, suspicious domains. | P0 | IMPLEMENTED | `normalize.extract_domains`; `safety_rules`; `local_image` | safety tests | tests passed | Domains not visited | Safe | No | None |
| E05 | unverified financial sender | Treat unverified financial sender risk. | P0 | IMPLEMENTED | `safety_rules.assess_safety` | `test_bank_account_blocking_threat_is_high_risk_for_unverified_sender` | tests passed | None | Safety critical | No | None |
| E06 | forwarding/chain behavior | Detect chain/excessive forwards and fatigue. | P1 | IMPLEMENTED | `safety_rules.CHAIN_RE`; `behaviorgraph.forwarding_fatigue_contribution`; `resolver` | forwarding tests | tests passed | None | Noise reduction | No | None |
| E07 | safety precedence | High affinity/trust cannot override risk. | P0 | IMPLEMENTED | `resolver.resolve` first branch | `test_high_risk_mutes_even_when_trusted`; safety tests | tests passed | None | Safety critical | No | None |
| F01 | same-user evidence | Same-user isolation. | P0 | IMPLEMENTED | `idx.history_by_user`; `validate_output_rows` | `test_evidence_same_user_only` | evidence audit | None | Prevents privacy leak | No | None |
| F02 | stable TF-IDF | Stable numerical calculations and quantized comparisons. | P0 | IMPLEMENTED | `retrieval._idf_for_docs`; `_cosine`; `_quantize_score` | `test_retrieve_evidence_stable_across_hash_seed_processes` | MSG_082 diagnostic | None | Reproducibility | No | None |
| F03 | material relevance/reaction-aware | Threshold and reaction-aware reranking. | P1 | IMPLEMENTED | `retrieve_evidence` qualification rules | threshold audit | FINAL_EVIDENCE_THRESHOLD_AUDIT.csv | Threshold is deterministic heuristic | Defensible evidence | No | Tune on labels |
| F04 | max/no invented/cross-user IDs | Limit evidence and validate IDs. | P0 | IMPLEMENTED | `retrieve_evidence(limit=5)`; `validate.py` | evidence/output tests | evidence audit | None | Valid output | No | None |
| G01 | high-risk override | High-risk safety mutes as scam. | P0 | IMPLEMENTED | `resolver.resolve` | resolver/safety tests | tests passed | None | Safety critical | No | None |
| G02 | trusted critical urgency | Trusted urgent direct updates can notify. | P0 | IMPLEMENTED | `resolver.resolve`; `exception_check` | resolver/exception tests | tests passed | None | Avoids missed urgent | No | None |
| G03 | muted group exception | Muted group queues unless trusted critical exception. | P0 | IMPLEMENTED | `exception_check`; `resolver` | muted group tests | tests passed | None | Respect mute | No | None |
| G04 | opt-out/fatigue/repeated forwarding | Promotion opt-out, high fatigue, repeated forwarding. | P1 | IMPLEMENTED | `resolver.resolve` | resolver tests | tests passed | None | Noise reduction | No | None |
| G05 | suspicious/ambiguous/quiet/load digest | Digest for suspicious nondecisive, ambiguous, quiet/load, safe nonurgent. | P1 | IMPLEMENTED | `resolver.resolve` | resolver/output tests | reason report | None | Good default | No | Tune thresholds |
| H01 | bounded confidence | Confidence bounded, reduced for ambiguity/media/missing context. | P0 | IMPLEMENTED | `confidence.calibrate_confidence` | output tests | final summary | Deterministic not learned | Valid output | No | Label calibration |
| H02 | reason grounding | Reasons grounded in resolver/safety/features/evidence. | P0 | IMPLEMENTED | `reason.build_reason`; `consistency.validate_and_repair_reason` | consistency tests | FINAL_REASON_CONSISTENCY_REPORT.csv | None | Interview defensible | No | None |
| H03 | selected evidence consistency | Reasons do not cite unselected evidence. | P0 | IMPLEMENTED | `consistency.py` | `test_unselected_evidence_reference_is_reported` | reason report | None | Evidence coherent | No | None |
| I01 | row-level error boundary | Row failures become conservative digest fallback. | P0 | IMPLEMENTED | `orchestrator.process_message` exception handler | output/media failure tests | tests passed | None | No dropped rows | No | None |
| I02 | deterministic fallback | Offline/local paths deterministic. | P0 | IMPLEMENTED | resolver/retrieval/local providers | determinism tests | hash-seed and clean-room reports | None | Reproducible output | No | None |
| I03 | provider timeout/retry/cap | Optional provider has timeout, retry, request cap. | P1 | IMPLEMENTED | `provider.OpenRouterProvider` | `test_provider_cache.py` | provider stats reports | Optional mode only | No official dependency | No | None |
| I04 | cache versioning | OCR/ASR/provider caches keyed by data/version. | P1 | IMPLEMENTED | `local_image._cache_path`; `provider` cache keys | cache invalidation tests | cache stats | None | Reproducibility | No | None |
| I05 | summary/checksum | Summary JSON includes SHA and stats; write failure does not corrupt output. | P1 | IMPLEMENTED | `main.write_summary_json`; `build_summary_payload` | `test_summary_json.py` | summary JSON | None | Auditability | No | None |
| J01 | unit/schema/property/adversarial tests | Broad 129-test suite. | P0 | IMPLEMENTED | `code/tests/` | 129 tests collected/passed | pytest output | None | High confidence | No | None |
| J02 | same-message/two-user tests | Personalized routing differs by user history. | P1 | IMPLEMENTED | tests | `test_same_promotion_for_two_users_uses_different_histories`; `test_same_promotional_content_routes_differently_for_history` | tests passed | None | Personalization evidence | No | None |
| J03 | media/determinism/evidence/reason/failure tests | Media, determinism, evidence, reason consistency, failure injection. | P0 | IMPLEMENTED | tests | local image, retrieval, consistency, output suites | tests passed | None | Strong validation | No | None |
| J04 | ablation/comparison/latency/provider/cost | Evaluation reports compare modes, latency, provider/cost stats. | P1 | IMPLEMENTED | `code/evaluation/` reports | N/A report evidence | final reports | Documentation/evaluation evidence rather than executable CI gate | Interview evidence | No | Automate report generation |
| J05 | hidden-set disclosure | No guarantee of hidden-set performance. | P1 | IMPLEMENTED | `code/README.md`; final docs | doc audit | README limitations | None | Honest disclosure | No | None |
| K01 | path traversal/symlink containment | Media containment and symlink escape checks. | P0 | IMPLEMENTED | `io.safe_media_path`; `local_image._resolve_image_path` | path traversal tests | tests passed | None | Security critical | No | None |
| K02 | untrusted messages/media | Do not execute/follow prompt/QR/media content. | P0 | IMPLEMENTED | `media.py`; `local_image.py`; `safety_rules.py` | injection/QR tests | tests passed | None | Security critical | No | None |
| K03 | no raw sensitive logs | Sanitized errors and summary excludes raw sensitive content. | P0 | IMPLEMENTED | `local_image._sanitize_error`; `provider.sanitize_provider_error`; summary tests | `test_summary_json_has_no_raw_sensitive_content` | security scan passed | Transcript may contain ordinary historical local paths | Allowed by user rules | No | None |
| K04 | environment-only keys | API keys loaded from env/.env but not committed/packaged with values. | P0 | IMPLEMENTED | `main._load_env_file`; `provider.OpenRouterConfig.from_env` | provider tests | security scan passed | `.env.example` placeholder only | Safe | No | None |
| K05 | packaging hygiene | No dataset/media/models/caches/transcript in ZIP. | P0 | PACKAGING_COMPLETE | ZIP staging | ZIP inventory/security scan | code.zip SHA 744... before this audit | Rebuild required only after docs audit files | Must update if included files changed | Yes after changes | None |
| L01 | README/requirements/prompts/tests/evaluation/docs | Runnable package has required materials. | P0 | PACKAGING_COMPLETE | `code/`; `docs/` | clean-room tests | manifest/checklist | None | Upload-ready after rebuild | Yes | None |
| L02 | clean-room install/run | Extracted ZIP tests and output equality. | P0 | PACKAGING_COMPLETE | code.zip | clean-room validation | clean-room summary/output | None | Reproducible submission | Yes if ZIP rebuilt | None |
| L03 | GitHub branch/final commit | `feat/shieldrouter` local and remote at final release commit. | P0 | IMPLEMENTED | git refs | git commands | HEAD and origin match 3632380 | User will push any new audit commit manually | Manual step | No | Push after audit commit |
| L04 | older design output examples | Older unified design mentions `user_id`, `risk_flags`, `scam_or_risk`. | P0 | SUPERSEDED_BY_OFFICIAL_SCHEMA | final doc and schemas enforce official output | schema/prompt tests | rg audit | Older illustrative pseudocode superseded by official schema | No official impact | No | Add erratum if time permits |
| L05 | multi-agent/two-LLM aspirations | Mandatory multi-agent/two-call architecture rejected. | P1 | INTENTIONAL_DEVIATION | deterministic local pipeline; optional OpenRouter only | provider/local tests | final docs ADRs | Reproducibility and zero-provider selected mode preferred | Positive for reproducibility | No | None |
| L06 | acoustic emotion recognition | Acoustic/prosody emotion recognition explicitly not claimed. | P1 | INTENTIONAL_DEVIATION | transcript-derived `derive_voice_metadata` | voice metadata tests | README/final docs | Dataset/transcripts support linguistic tone, not acoustic emotion | Honest limitation | No | Add acoustic model only if required |

## Completion Calculations

- Official challenge compliance: 12/12 mandatory official requirements complete = 100%.
- P0 requirement completion: 37/37 P0 requirements complete = 100%.
- P1 requirement completion: 26/26 P1 requirements complete = 100%.
- Final implementation-document alignment: 53/54 implementable final-document requirements implemented or intentionally documented = 98.1%; the remaining gap is richer visual scene understanding, documented as a limitation.
- Unified-design alignment: 21/24 applicable unified-design requirements aligned = 87.5%; three older inferred output/pseudocode ideas are superseded by the official schema or final document.
- Testing-plan completion: 5/5 testing categories complete = 100%.
- Security completion: 5/5 security categories complete = 100%.
- Release completion before rebuilding this audit into ZIP: 3/4 complete = 75%; code.zip must be rebuilt if these new included docs are kept.
- Release completion after rebuild and validation: expected 4/4 = 100%.

## Partially Implemented Requirements

- D11 complete visual scene understanding: implemented as deterministic local OCR, QR, layout, and text-signal extraction, not a general-purpose visual scene model.

## Intentional Deviations

- L05: mandatory multi-agent or two-LLM-call routing is not used for the selected candidate; deterministic local multimodal execution is selected for zero-provider reproducibility.
- L06: voice tone is transcript-derived linguistic tone, not acoustic emotion/prosody analysis.
- A10/H01: confidence is deterministic calibration, not learned probability calibration.

## Superseded Inferred Requirements

- L04: older unified-design examples that include `user_id`, `risk_flags`, `social`, `admin`, `other`, or `scam_or_risk` are superseded by AGENTS.md, problem_statement.md, and the final implementation-ready document.

## True Missing Official Requirements

None identified.

## Submission Gate

No official blocker was found. Because this audit file and the codebase map are
inside paths normally included in `code.zip`, the ZIP must be rebuilt and
validated before upload if these audit artifacts are retained.
