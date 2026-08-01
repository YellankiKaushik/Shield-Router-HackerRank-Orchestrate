# ShieldRouter Final Evaluation Report

## Objective

ShieldRouter routes WhatsApp-style multimodal messages to `notify`, `digest`, or `mute` for the HackerRank Orchestrate Message Notification Router challenge. The final output must contain exactly one row per `dataset/messages.csv` message with `message_id,action,message_type,reason,confidence,evidence_message_ids`.

## Final Architecture

The selected candidate is local multimodal. Text routing is deterministic and personalized. Image processing uses local RapidOCR with ONNXRuntime plus OpenCV QR detection. Voice notes use local Faster-Whisper. Optional OpenRouter advisory enrichment remains available but is not the selected release candidate.

Source-of-truth hierarchy:

1. Participant dataset files under `dataset/`.
2. Local media bytes resolved from `images.csv` and `voice_notes.csv`.
3. Deterministic safety, context, evidence, synthesis, resolver, confidence, and reason code.
4. Evaluation reports under `code/evaluation/`, never production-routing inputs.

Production routing uses `load_routing_dataset()`, which excludes `sample_messages.csv` and `output.csv`. The leakage audit is in `final_leakage_audit.txt`.

## Safety Gate

Safety receives message text, locally extracted media facts, forwarded count, and minimal sender legitimacy. It does not use personalization to reduce safety risk. It detects credential theft, OTP/PIN/password/login-code requests, payment detail pressure, suspicious domains, refund/reward pressure, account-blocking threats, prompt injection, and chain forwarding.

## BehaviorGraph

BehaviorGraph is implemented as deterministic feature computation over CSV indexes, not a graph database. It calculates trust, affinity, fatigue, promotion opt-out, group mute, quiet hours, recent notification load, direct mention, urgency, repetition, relationship strength, and missing context.

## Evidence Retrieval

Evidence is retrieved from same-user `message_history.csv` only. Retrieval uses token similarity plus same sender/group/business/media context and prior user interaction signals. The final evidence audit found 106 rows using evidence, 0 invalid evidence rows, and 0 weak-evidence rows.

## Local Image OCR/QR

For image rows, ShieldRouter resolves `media_id` through `images.csv`, validates that the resolved path remains inside the dataset directory, rejects traversal/symlink escapes, validates image type and size, reads actual bytes, decodes with Pillow/OpenCV, runs RapidOCR lazily, detects QR codes locally with OpenCV, extracts URLs/domains/phones/prices/dates/safety language, and caches by media SHA-256 plus OCR/schema/preprocessing versions. QR destinations are never visited.

Image stats: 15 attempted, 15 extracted, 0 failures, 15 cache hits in final run, 0 QR codes detected. OCR confidence min 0.0, mean 0.7856, max 0.998. Weak or empty OCR rows: `msg_005`, `msg_030`, `msg_029`.

## Local Voice

Voice notes use Faster-Whisper with local-files-only mode for selected zero-network runs. Transcripts are cached by audio SHA-256 plus model/device/compute settings. Final run stats: 8 voice attempts, 8 successes, 8 transcript cache hits, 0 failures.

## Resolver Precedence

The deterministic resolver owns the final action:

1. High-risk safety override -> `mute`.
2. Trusted critical direct urgency -> `notify`.
3. Trusted direct response request -> `notify`.
4. Trusted time-critical update -> `notify`.
5. Promotion opt-out or repeated dismissal -> `mute`.
6. Severe fatigue for low-value classes -> `mute`.
7. Repeated forwarding pattern -> `mute`.
8. Non-decisive suspicious content -> `digest`.
9. Ambiguous content -> `digest`.
10. Safe non-urgent content -> `digest`.

## Confidence

Confidence is deterministic calibration from rule agreement, safety strength, urgency clarity, evidence, trust/fatigue/opt-out, media availability, ambiguity, missing context, and errors. It is not a learned probability.

## Sample Metrics

Offline:

- Action accuracy: 0.9333
- Action macro F1: 0.9351
- Message-type accuracy: 0.9000
- Message-type macro F1: 0.8955
- Notify precision/recall: 1.0 / 0.8889
- Image action/type correctness: 0.8 / 0.6
- Voice action/type correctness: 0.6667 / 0.6667

Local voice:

- Action accuracy: 0.9667
- Action macro F1: 0.9680
- Message-type accuracy: 0.9333
- Message-type macro F1: 0.9209
- Notify precision/recall: 1.0 / 1.0
- Image action/type correctness: 0.8 / 0.6
- Voice action/type correctness: 1.0 / 1.0

Local multimodal:

- Action accuracy: 1.0000
- Action macro F1: 1.0000
- Message-type accuracy: 1.0000
- Message-type macro F1: 1.0000
- Notify precision/recall: 1.0 / 1.0
- Image action/type correctness: 1.0 / 1.0
- Voice action/type correctness: 1.0 / 1.0

OpenRouter hybrid:

- Existing artifact validates at 110 rows.
- Sample metrics were not rerun during the final freeze because the selected audit was zero-network and OpenRouter is optional.

Action confusion matrices are stored in `sample_eval_offline_current.json`, `sample_eval_local_voice_current.json`, and `sample_eval_local_multimodal.json`. Local multimodal confusion matrices are perfect on the labeled sample.

## Ablation Comparison

Full-output distributions:

- Offline: digest 62, mute 40, notify 8.
- Local voice: digest 59, mute 41, notify 10.
- Local multimodal: digest 53, mute 45, notify 12.
- OpenRouter hybrid artifact: digest 60, mute 41, notify 9.

Local multimodal was selected because it matched or improved sample performance, inspected actual image bytes, preserved local voice gains, made zero provider requests, validated 110/110 rows, extracted all 15 images, processed all 8 voice notes, and reran byte-identically.

## Final Full Run

- Tests: 76 passed.
- Input validation: 110 messages.
- Output validation: 110 rows.
- Unique IDs: 110.
- Actions: digest 53, mute 45, notify 12.
- Message types: scam 31, unknown 18, promotion 13, forward 10, greeting 9, event 7, business_update 7, personal 6, urgent 5, payment 3, spam 1.
- Confidence: min 0.55, mean 0.7299, max 0.95.
- Evidence usage: 106 rows.
- Provider requests: 0.
- Runtime: 0.1997s first final temp run, 0.1727s second final temp run.
- SHA-256: `A819A2AF4F32687419F342E18D5320C0C3EBB41A2F4385430D153E5842E4686D`.

## Audits

- Leakage/hardcoding: PASS after routing-only loader correction.
- Changed decisions: 8 reviewed, all supported.
- Media consistency: 15 image and 8 voice rows reviewed, all internally consistent.
- Evidence validity: PASS, 0 invalid, 0 weak.
- Secret hygiene: PASS; generated caches and environments are ignored.

## Known Limitations

- OCR can be weak or empty on low-text photos; ShieldRouter marks these as low-information instead of inventing captions.
- Scene understanding is limited to OCR, QR, metadata, and deterministic text analysis.
- Faster-Whisper selected zero-network runs require local model availability beforehand.
- Confidence is deterministic calibration, not learned probability calibration.
- Perfect sample-set results do not guarantee hidden-set performance.
