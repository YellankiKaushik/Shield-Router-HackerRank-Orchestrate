# ShieldRouter

ShieldRouter is a deterministic Python CLI for the HackerRank Orchestrate August 2026 Message Notification Router. It reads the official participant CSVs from `dataset/`, builds local personalization and safety context, inspects local voice and image media in zero-network modes, and writes the required six-column `output.csv`.

The current selected candidate is `code/evaluation/baselines/local_multimodal_tuned.csv`, promoted to root `output.csv` after validation. The previous local-voice root output is preserved at `code/evaluation/baselines/pre_local_multimodal_output.csv`.

## Architecture

1. `io.py` validates exact CSV headers, IDs, timestamps, booleans, and media path containment.
2. `indexes.py` builds users, groups, memberships, businesses, business history, message history, events, daily load, image, and voice-note indexes.
3. `normalize.py` normalizes whitespace/Unicode and extracts URLs/domains while treating message content as untrusted data.
4. `safety_rules.py` detects OTP/PIN/password/login-code requests, wallet/card-detail pressure, payment/QR pressure, suspicious domains, account-pressure language, prompt injection, and forwarding chains.
5. `local_image.py` lazily decodes actual image bytes, validates type/size/path safety, runs RapidOCR through ONNXRuntime, detects QR codes with OpenCV, extracts structured `LocalImageFacts`, and caches by media SHA-256 plus OCR/schema/preprocessing versions.
6. `provider.py` provides optional OpenRouter advisory support, local Faster-Whisper transcription, and the zero-network `LocalMultimodalProvider`.
7. `behaviorgraph.py`, `retrieval.py`, `fallback_synthesis.py`, `resolver.py`, `confidence.py`, and `reason.py` compute context, evidence, deterministic synthesis, final action, confidence, and grounded reasons.

The resolver owns the final `notify`, `digest`, or `mute` action. OCR, Whisper, and optional provider outputs are facts only.

## Setup

Use Python 3.12. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r code\requirements.txt
```

Local image processing requires `rapidocr`, `onnxruntime`, `opencv-python-headless`, and `Pillow`. Local voice transcription requires `faster-whisper` and an already available local model cache.

For the selected zero-network mode, `LOCAL_WHISPER_LOCAL_FILES_ONLY=1` is enforced and model fallback is disabled. If the Faster-Whisper model is not already available locally, the first selected-mode run reports an explicit media failure instead of downloading during routing. Model download or cache warmup must be handled before a zero-network reproduction run.

## Commands

Validate inputs:

```powershell
python code/main.py validate-input --dataset dataset
```

Offline text/context mode:

```powershell
python code/main.py run --dataset dataset --output code/evaluation/baselines/offline_tuned.csv --offline
```

Local voice mode:

```powershell
python code/main.py run --dataset dataset --output code/evaluation/baselines/local_voice_tuned.csv --local-voice --cache-dir code/.shieldrouter_cache
```

Local multimodal mode, selected candidate:

```powershell
python code/main.py run --dataset dataset --output code/evaluation/baselines/local_multimodal_tuned.csv --local-multimodal --cache-dir code/.shieldrouter_cache
python code/main.py validate-output --dataset dataset --output code/evaluation/baselines/local_multimodal_tuned.csv
```

Zero-network reproduction:

```powershell
python code/main.py run --dataset dataset --output .tmp/local_multimodal_rerun.csv --local-multimodal --cache-dir code/.shieldrouter_cache
```

The rerun should be byte-identical to `code/evaluation/baselines/local_multimodal_tuned.csv` when inputs and code are unchanged.

Optional OpenRouter hybrid mode:

```powershell
python code/main.py smoke-online --dataset dataset --cache-dir code/.shieldrouter_cache
python code/main.py run --dataset dataset --output code/evaluation/baselines/hybrid_openrouter.csv --online --cache-dir code/.shieldrouter_cache
```

OpenRouter mode requires `AI_PROVIDER=openrouter` and `OPENROUTER_API_KEY`. It uses a strict 35-request cap and deterministic fallback. Do not use it for zero-network reproduction.

Evaluation and tests:

```powershell
python code/main.py evaluate-sample --dataset dataset --local-multimodal --cache-dir code/.shieldrouter_cache --report code/evaluation/sample_eval_local_multimodal.json --errors code/evaluation/sample_error_analysis_local_multimodal.csv
python -m pytest code/tests -q -p no:cacheprovider --basetemp=.tmp/pytest
```

Current test count: 76 passing.

## Output Contract

Predictions are generated only for rows in `dataset/messages.csv`. The output columns are exactly:

```text
message_id,action,message_type,reason,confidence,evidence_message_ids
```

Allowed actions are `notify`, `digest`, and `mute`. Allowed message types are `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, and `unknown`.

`evidence_message_ids` contains semicolon-separated IDs from `dataset/message_history.csv` for the same receiving user, or `none`.

## Validated State

- 110 input rows and 110 valid output rows.
- Local multimodal attempts all 15 image messages and succeeds on all 15.
- RapidOCR is lazy-loaded only for image rows and uses local ONNX model files.
- OpenCV QR detection runs locally; no QR destinations are opened.
- Local Faster-Whisper processes all 8 voice notes from cache in the validated run.
- Provider request count is exactly zero in `--local-voice` and `--local-multimodal`.
- Local multimodal deterministic rerun SHA-256: `A819A2AF4F32687419F342E18D5320C0C3EBB41A2F4385430D153E5842E4686D`.
- The final code package is expected to contain code and documentation; the evaluation dataset is provided externally by the challenge environment.

## Reports

- `code/evaluation/local_image_comparison.csv` audits all 15 image messages, OCR confidence, weak OCR, QR presence, extracted dates/prices/domains, safety signals, confidence before/after, and changed decisions.
- `code/evaluation/sample_eval_local_multimodal.json` contains labeled sample metrics for the selected candidate.
- Baseline artifacts are stored under `code/evaluation/baselines/`.

## Known Limitations

- OCR quality is weak or empty on some low-text photos/posters; those rows are explicitly marked low-information and still routed with message text and history.
- Scene understanding is limited to locally extracted OCR/QR/metadata facts. The local pipeline does not invent captions.
- Faster-Whisper requires local model files; failures are explicit, lower confidence, and preserve rows.
- OpenRouter hybrid remains optional and is not part of the selected zero-network candidate.
