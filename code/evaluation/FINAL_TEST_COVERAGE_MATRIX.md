# Final Test Coverage Matrix

Last full run: `127 passed`.

| Category | Implemented tests | Files | Cases covered | Result | Remaining limitation |
|---|---|---|---|---|---|
| Unit | Yes | `test_behaviorgraph.py`, `test_resolver.py`, `test_exception_check.py`, `test_consistency.py`, `test_voice_metadata.py` | novelty boundaries, transaction relationship, forwarding fatigue, resolver precedence, muted-group exception, reason consistency, transcript-derived voice tone | Passed | Hidden labels unavailable |
| Schema/property | Yes | `test_schemas.py`, `test_io.py`, `test_output.py`, `test_summary_json.py` | exact output schema, official enums, malformed input schema, 110-row preservation, summary schema and SHA | Passed | Summary JSON is operational, not a formal JSON Schema file |
| Sample evaluation | Yes | `code/main.py evaluate-sample`, `sample_eval_final_*.json` | labeled sample action/type metrics, image/voice correctness, evidence validity | Passed | Sample set is small and not the hidden set |
| Adversarial | Yes | `test_safety_rules.py`, `test_online_ai.py`, `test_local_image.py`, `test_voice_metadata.py` | OTP/PIN/password theft, payment/QR pressure, suspicious-domain pressure, prompt injection in text/OCR/voice transcript, high affinity cannot override theft | Passed | Rule lists are deterministic heuristics |
| Same-message/two-user personalization pair | Yes | `test_output.py`, `test_local_image.py` | same promotion routes differently for users with different histories/preferences | Passed | Synthetic fixture covers one promotional family |
| Media | Yes | `test_local_image.py`, `test_openrouter_media_voice.py`, `test_cli_local_voice.py`, `test_voice_metadata.py` | corrupt image, missing image/audio, empty OCR, empty transcript, prompt injection in OCR/voice, legitimate payment receipt, verified transaction update, event poster, missing Whisper cache | Passed | No acoustic emotion/prosody analysis |
| Determinism | Yes | `test_output.py`, `test_local_image.py`, `test_exception_check.py`, final candidate rerun | offline byte identity, local multimodal byte identity, exception rerun, final candidate byte comparison | Passed | Determinism assumes stable local model/cache versions |
| Evidence | Yes | `test_retrieval.py`, `test_online_ai.py`, `test_output.py`, final reports | same-user retrieval, candidate evidence restriction, valid evidence IDs, `none` fallback | Passed | Lexical TF-IDF-style retrieval, not embeddings |
| Reason consistency | Yes | `test_consistency.py`, `FINAL_REASON_CONSISTENCY_REPORT.csv` | contradiction detection, evidence reference validation, deterministic reason repair path, 110-row report | Passed | Semantic contradiction detection remains structured-rule based |
| Failure injection | Yes | `test_online_ai.py`, `test_local_image.py`, `test_cli_local_voice.py`, `test_summary_json.py`, `test_output.py` | malformed provider JSON, unavailable provider, invalid/corrupt media, summary write failure, per-row failure preserving outputs | Passed | External provider smoke depends on configured credentials |

Explicit coverage checklist:

- OTP/PIN/password theft: `test_safety_rules.py`, `test_online_ai.py`
- Payment/QR pressure: `test_safety_rules.py`, `test_local_image.py`
- Suspicious-domain account pressure: `test_safety_rules.py`
- Prompt injection in text: `test_online_ai.py`
- Prompt injection in OCR text: `test_local_image.py`
- Prompt injection in voice transcript: `test_online_ai.py`
- Legitimate payment receipt: `test_local_image.py`
- Legitimate verified transaction update: `test_local_image.py`, `test_behaviorgraph.py`
- Legitimate event poster: `test_local_image.py`
- Muted-group trusted urgent direct mention: `test_exception_check.py`, `test_resolver.py`
- Quiet-hours noncritical downgrade: `test_exception_check.py`, `test_resolver.py`
- Critical-urgency quiet-hours exception: `test_exception_check.py`, `test_resolver.py`
- Same promotion for two users: `test_output.py`, `test_local_image.py`
- High affinity cannot override credential theft: `test_resolver.py`, `test_exception_check.py`
- Corrupt image: `test_local_image.py`
- Missing image: `test_openrouter_media_voice.py`, `test_local_image.py`
- Missing audio: `test_online_ai.py`
- Empty OCR: `test_local_image.py`
- Empty transcript: `test_openrouter_media_voice.py`, `test_voice_metadata.py`
- Missing Whisper model cache: `test_cli_local_voice.py`, `test_openrouter_media_voice.py`
- Malformed provider JSON: `test_online_ai.py`, `test_openrouter_media_voice.py`
- Unavailable provider: `test_online_ai.py`
- Malformed input schema: `test_io.py`
- Per-row failure preserving 110 outputs: `test_output.py`, `test_local_image.py`
- Zero-provider local multimodal operation: `test_local_image.py`, final summary JSON
