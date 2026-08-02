# ShieldRouter

ShieldRouter is a deterministic Python CLI for the HackerRank Orchestrate August 2026 Message Notification Router. It reads the official participant CSVs from `dataset/`, builds local personalization and safety context, inspects local voice and image media in zero-network modes, and writes the required six-column `output.csv`.

## Sprint 2 final-alignment notes

- Selected candidate: `code/evaluation/baselines/final_design_aligned.csv`.
- Reproducibility fix: evidence retrieval now uses sorted token accumulation, `math.fsum`, four-decimal quantized comparisons, and a `0.13` relational-useful evidence threshold. Voice ASR text canonicalizes the common `check out`/`checkout` split before routing.
- Structured run summaries are available with `--summary-json <path>`. The summary includes counts, confidence ranges, media/cache/provider statistics, runtime, output SHA-256, model/cache metadata, timestamp, and commit when available. It intentionally excludes raw message text, OCR text, voice transcripts, API keys, credentials, and absolute private paths.
- Voice metadata is transcript-derived only: `detected_tone` is `urgent`, `neutral`, `calm`, or `unknown`, and `detected_pressure_language` marks coercive or manipulation wording. ShieldRouter does not perform acoustic emotion recognition, pitch analysis, stress detection, speaker identity, or prosody analysis.
- BehaviorGraph now exposes novelty, highest same-user history similarity, transaction relationship/strength, bounded forwarding fatigue, and selected evidence engagement counts in trace output.
- Muted-group exception checking is an explicit stage before the deterministic resolver. High-risk safety still blocks notification eligibility.
- Reason consistency validation runs inside the routing path and reports zero unresolved contradictions across the final 110-row candidate.

The current selected candidate is `code/evaluation/baselines/final_design_aligned.csv`, promoted to root `output.csv` after validation. The previous local-voice root output is preserved at `code/evaluation/baselines/pre_local_multimodal_output.csv`.

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

Local image processing requires `rapidocr`, `onnxruntime`, `opencv-python-headless`, and `Pillow`. RapidOCR ships the required ONNX model assets with the installed Python package.

Local voice transcription requires `faster-whisper` and a prepared local Faster-Whisper model cache. For the selected zero-network mode, `LOCAL_WHISPER_LOCAL_FILES_ONLY=1` is enforced and model fallback is disabled. If the Faster-Whisper model is not already available locally, the selected-mode run reports explicit media failures instead of downloading during routing.

Prepare local models once before a zero-network reproduction run:

```powershell
# Optional: choose a cache outside this repository.
$env:HF_HOME = "$env:LOCALAPPDATA\ShieldRouter\hf-cache"
python code/main.py prepare-models
```

`prepare-models` initializes RapidOCR and downloads/caches the configured Faster-Whisper model, defaulting to `LOCAL_WHISPER_MODEL` or `small`. It does not require an API key, prints model names and cache locations, and refuses to write Hugging Face model files under the repository root.

## Commands

Validate inputs:

```powershell
python code/main.py validate-input --dataset dataset
python code/main.py run --dataset dataset --output code/evaluation/baselines/final_design_aligned.csv --local-multimodal --summary-json code/evaluation/final_design_aligned_summary.json
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
python code/main.py run --dataset dataset --output code/evaluation/baselines/final_design_aligned.csv --local-multimodal --cache-dir code/.shieldrouter_cache
python code/main.py validate-output --dataset dataset --output code/evaluation/baselines/final_design_aligned.csv
```

Zero-network reproduction:

```powershell
python code/main.py run --dataset dataset --output .tmp/local_multimodal_rerun.csv --local-multimodal --cache-dir code/.shieldrouter_cache
```

The rerun should be byte-identical to `code/evaluation/baselines/final_design_aligned.csv` when inputs and code are unchanged.

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

Current test count: 129 passing.

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
- Local multimodal deterministic rerun SHA-256: `CD8B26364C30C86D8E25E27C9E2A2D2E9624F7159F0D1236540AF17E0C5DE55E`.
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
