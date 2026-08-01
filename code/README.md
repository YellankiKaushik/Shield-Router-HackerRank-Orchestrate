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
python code/main.py validate-output --dataset dataset --output output.csv
python code/main.py trace --dataset dataset --message-id msg_023 --offline
python -m pytest code/tests -q
```

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

## Limitations

- Image content is not actually inspected with OCR/vision in this offline baseline.
- Voice notes are not transcribed in this offline baseline.
- Contextual synthesis is deterministic rules rather than a restricted model.
- Confidence is calibrated from internal agreement signals, not learned probabilities.

## Next Phases

- Add restricted model safety assessment that receives only message/media/minimal sender data.
- Add actual image inspection with OCR/vision and cache outputs by media hash.
- Add voice-note transcription and urgency/tone extraction.
- Add structured contextual synthesis that receives safety read-only plus BehaviorGraph and evidence facts.
- Add adversarial evaluation, ablations, and final packaging checks.
