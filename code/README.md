# ShieldRouter Offline Baseline

ShieldRouter is a deterministic Python CLI for HackerRank Orchestrate August 2026 Message Notification Router. It reads the official participant CSVs from `dataset/`, builds local context indexes, applies non-overridable safety rules, computes BehaviorGraph-style personalization features, retrieves same-user historical evidence, resolves a final action with code-only precedence, and writes the exact required `output.csv`.

## Architecture

1. `io.py` validates exact CSV headers, IDs, timestamps, booleans, and media path containment.
2. `indexes.py` builds users, groups, memberships, businesses, business history, message history, events, daily load, image, and voice-note indexes.
3. `normalize.py` normalizes whitespace/Unicode and extracts URLs/domains while treating message content as untrusted data.
4. `safety_rules.py` detects OTP/PIN/password/login-code requests, payment/QR pressure, suspicious domains, account-pressure language, prompt injection, and forwarding chains.
5. `behaviorgraph.py` calculates trust, affinity, fatigue, opt-out, group mute, quiet-hours, recent load, urgency, direct mention, repetition, missing context, and media availability.
6. `retrieval.py` performs deterministic same-user TF-IDF-style token retrieval and metadata reranking, returning at most five valid historical IDs.
7. `fallback_synthesis.py` derives urgency, direct mention, message type, preliminary action, ambiguity, and grounded facts without an external model.
8. `resolver.py` enforces final precedence. The resolver, not a model, owns the submitted action.
9. `confidence.py`, `reason.py`, and `validate.py` calibrate score, explain decisions, and enforce the six-column output contract.

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r code\requirements.txt
```

If `python` is not on PATH, use any Python 3.12-compatible interpreter. The offline router itself uses only the Python standard library; `pytest` is required for the test suite.

## Commands

```powershell
python code/main.py validate-input --dataset dataset
python code/main.py run --dataset dataset --output output.csv --offline
python code/main.py run --dataset dataset --output code/evaluation/baselines/local_voice_tuned.csv --local-voice --cache-dir code/.shieldrouter_cache
python code/main.py validate-output --dataset dataset --output output.csv
python code/main.py trace --dataset dataset --message-id msg_023 --offline
python code/main.py evaluate-sample --dataset dataset --report code/evaluation/sample_eval_tuned.json --errors code/evaluation/sample_error_analysis.csv
python -m pytest code/tests -q
```

Optional hybrid smoke tests require `AI_PROVIDER=openrouter` and `OPENROUTER_API_KEY`. The API key is read from the environment or `.env`; it is never printed. OpenRouter calls use the OpenAI-compatible `https://openrouter.ai/api/v1` endpoint, strict structured JSON schema output where supported, provider parameter enforcement, `provider.data_collection=deny`, a default 35-request run cap, one retry for HTTP 429/5xx, and no retry for HTTP 400/401/402/403/404.

```powershell
python code/main.py smoke-online --dataset dataset --cache-dir code/.shieldrouter_cache
python code/main.py run --dataset dataset --output code/evaluation/baselines/hybrid_openrouter.csv --online --cache-dir code/.shieldrouter_cache
```

The online path preserves deterministic offline fallback. Do not run the full dataset online until the smoke test confirms one text request, one real image request, one local voice transcription, structured validation, actual returned model reporting, and cache reruns with zero new OpenRouter requests.

## Input/Output Contract

Input predictions are generated only for rows in `dataset/messages.csv`. The output columns are exactly:

```text
message_id,action,message_type,reason,confidence,evidence_message_ids
```

Allowed actions are `notify`, `digest`, and `mute`. Allowed message types are `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, and `unknown`.

`evidence_message_ids` contains semicolon-separated IDs from `dataset/message_history.csv` for the same receiving user, or `none`.

## Decision Precedence

1. High-confidence scam, credential theft, or integrity risk -> `mute`.
2. Legitimate trusted time-critical direct mention -> `notify`, including muted group or quiet-hours exceptions.
3. Explicit promotion opt-out, severe fatigue, or repeated dismissal -> `mute`.
4. Useful urgency during quiet hours or high notification load -> `digest`.
5. Safe and useful non-urgent content -> `digest`.
6. Ambiguous content -> `digest`.

## Offline Capabilities

The current baseline is fully offline and deterministic. It handles text, image references, and voice-note references as local attachments, validates referenced media paths, and marks per-row media issues conservatively without dropping rows. It does not perform OCR or transcription yet.

## Optional Hybrid Capabilities

The code includes a provider abstraction for external structured AI. The OpenRouter provider sends advisory semantic-enrichment requests only for selected messages: all image rows, at most 12 prioritized ambiguous/risky text rows, and ambiguous voice transcripts when budget remains. The model returns facts only; deterministic ShieldRouter safety, synthesis, resolver, confidence, evidence, and output validation still own the final `notify`, `digest`, or `mute` decision.

Voice notes are transcribed locally with `faster-whisper` using:

```text
LOCAL_WHISPER_MODEL=small
LOCAL_WHISPER_DEVICE=cpu
LOCAL_WHISPER_COMPUTE_TYPE=int8
```

The Whisper model lazy-loads only when a voice note is encountered, caches transcripts by audio SHA-256 and transcription options, preserves the original spoken language, and returns an explicit failure signal without dropping the output row. No OpenRouter transcription model is used.

For zero-network ablations, use `--local-voice` instead of `--online`. This mode does not construct the OpenRouter provider, does not read `OPENROUTER_API_KEY`, sets Whisper loading to local files only, forbids model fallback for that run, and asserts provider request counters stay at zero.

## Limitations

- Image content is not actually inspected unless the optional OpenRouter smoke test succeeds.
- Voice notes require `faster-whisper` and an available local model download/cache; failures lower confidence but preserve rows.
- The current validated submission candidate is the tuned offline output because the available API key failed authentication during smoke testing.
- Confidence is calibrated from internal agreement signals, not learned probabilities.

## Next Phases

- Add restricted model safety assessment that receives only message/media/minimal sender data.
- Add actual image inspection with OCR/vision and cache outputs by media hash.
- Add voice-note transcription and urgency/tone extraction.
- Add structured contextual synthesis that receives safety read-only plus BehaviorGraph and evidence facts.
- Add adversarial evaluation, ablations, and final packaging checks.
