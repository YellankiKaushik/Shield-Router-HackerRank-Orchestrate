# AI Judge Brief

## What problem does ShieldRouter solve?

ShieldRouter decides whether each incoming WhatsApp-style multimodal message should interrupt the user now, wait for a digest, or be muted as low-value or unsafe. It writes the required `output.csv` schema for all 110 challenge messages.

## Why is safety separated from personalization?

Safety is a non-overridable gate. Personalization can raise or lower urgency and usefulness, but it cannot make OTP theft, credential pressure, suspicious account links, or prompt injection safe.

## Why does the deterministic resolver own the final action?

The resolver makes final behavior auditable and reproducible. OCR, Whisper, and optional provider outputs contribute facts only; they do not choose `notify`, `digest`, or `mute`.

## How does BehaviorGraph work without a graph database?

It builds in-memory indexes from the CSV files and computes graph-like features: user affinity, trust, group membership, business history, fatigue, quiet hours, notification load, repeated patterns, and direct mentions.

## How is historical evidence prevented from crossing users?

Evidence retrieval indexes `message_history.csv` by receiving `user_id` and returns only candidates for the same user. The final evidence audit also verifies existence, same-user ownership, duplicate limits, and relevance.

## How are images processed?

The selected local multimodal mode resolves `media_id` through `images.csv`, validates path containment, rejects traversal/symlink escape, validates size/type, reads actual bytes, decodes locally, runs RapidOCR with ONNXRuntime, detects QR codes with OpenCV, extracts structured `LocalImageFacts`, and caches by media SHA-256 plus engine/schema/preprocessing versions.

## How are voice notes processed?

Voice notes are transcribed locally with Faster-Whisper in local-files-only mode. Transcripts are cached by audio SHA-256 and transcription settings. Transcript text is treated as untrusted input and passed through the same deterministic safety and synthesis pipeline.

## How does the system behave offline or after a media failure?

Selected local multimodal mode requires no external API. If media fails validation or extraction, ShieldRouter records an explicit error, lowers confidence, preserves the output row, and falls back to deterministic text/context routing.

## Why was local multimodal selected over OpenRouter hybrid?

Local multimodal produced 110 valid rows, passed 129 tests, extracted all 15 images, processed all 8 voice notes, made zero provider requests, reran byte-identically across process hash seeds, and improved labeled sample metrics over offline and local-voice ablations. OpenRouter remains optional but is not needed for the selected zero-network candidate.

## What are the main limitations?

OCR can be weak on low-text images; the system does not invent visual scene facts. Faster-Whisper must be locally available before zero-network reproduction. Confidence is deterministic calibration, not a learned probability. Perfect sample metrics do not guarantee hidden-set performance.

## How can the system scale beyond the hackathon?

The current design can scale by replacing CSV indexes with persistent stores, adding stronger local OCR/layout models, adding learned calibration from labeled feedback, expanding language-specific safety lexicons, and keeping the resolver/audit trail as the final accountable decision layer.
# Sprint 2 Judge Brief Addendum

ShieldRouter's selected mode is zero-network local multimodal. The final resolver remains deterministic and owns the final `notify`, `digest`, or `mute` action. OpenRouter is optional advisory functionality only and is not required for the selected submission path.

Final alignment features:

- BehaviorGraph exposes same-user novelty, highest history similarity, transaction relationship/strength from `user_business_history.csv`, bounded forwarding fatigue, and evidence engagement counts.
- Forwarded messages are not muted merely because they were forwarded. The mute branch requires chain-language, repeated content, muted/negative context, or selected evidence with negative reactions.
- Muted-group/direct-mention exception checking is explicit. Safe trusted critical direct mentions can notify even from muted groups or quiet-hour contexts; `high_risk` always blocks.
- Voice tone is transcript-derived linguistic metadata only: `urgent`, `neutral`, `calm`, or `unknown`, plus a pressure-language flag. There is no acoustic emotion, pitch, stress, speaker, or prosody analysis.
- Reason consistency validation checks final action/type/reason/safety/resolver/evidence together and produced zero unresolved contradictions across the 110-row final candidate.
- Evidence retrieval uses deterministic sorted-token scoring and a materiality margin for low-similarity relational evidence, preventing weak ASR-tokenization variants from changing selected evidence.
- `--summary-json` writes operational metrics atomically without raw message text, OCR text, voice transcripts, secrets, or absolute private paths.

Validation snapshot:

- Full suite: `129 passed`.
- Final candidate: `code/evaluation/baselines/final_design_aligned.csv`.
- Final root output SHA: `CD8B26364C30C86D8E25E27C9E2A2D2E9624F7159F0D1236540AF17E0C5DE55E`.
- Local multimodal media: 15/15 images succeeded, 8/8 voice notes succeeded.
- Provider requests in selected mode: zero.
- Labeled sample metrics: 1.0 action accuracy, 1.0 action macro F1, 1.0 type accuracy, 1.0 type macro F1.
- Hidden-set performance is not claimed.
