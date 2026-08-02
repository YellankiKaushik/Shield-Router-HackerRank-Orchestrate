# Final Operational Analysis

Selected mode: zero-network local multimodal.

- Rows: 110 input/output rows; unique IDs: 110.
- Action distribution: {'digest': 53, 'mute': 45, 'notify': 12}.
- Message-type distribution: {'business_update': 7, 'event': 7, 'forward': 10, 'greeting': 9, 'payment': 3, 'personal': 6, 'promotion': 13, 'scam': 31, 'spam': 1, 'unknown': 18, 'urgent': 5}.
- Confidence min/mean/max: 0.5498 / 0.7322172727272727 / 0.95.
- Evidence usage count: 106.
- Images attempted/succeeded/failed: 15/15/0.
- Voice attempted/succeeded/failed: 8/8/0.
- OCR cache hits: 15; transcript cache hits final run: 8; transcript cache hits cached rerun: 8.
- Provider requests/retries/fallbacks: 0/0/0.
- Final candidate runtime: 0.2503 seconds cached; fresh-cache reproducibility runs were about 49-50 seconds in the validation environment.
- Output SHA-256: CD8B26364C30C86D8E25E27C9E2A2D2E9624F7159F0D1236540AF17E0C5DE55E.
- Reproducibility: repository runs with default hash seed and `PYTHONHASHSEED` values `0`, `1`, `42`, and `12345` were byte-identical.

Cost and cache notes:

- Selected mode uses zero external-provider requests; selected API cost is zero.
- First-run model preparation can require a one-time Faster-Whisper download via `prepare-models` if the local model cache is absent.
- Fresh-cache runtime differs from fully cached runtime because Whisper/OCR facts are cached by content, model, and schema versions.
- Optional OpenRouter results, if present, are advisory experiments and are not the selected submission mode.
- No raw message text, OCR text, voice transcripts, API keys, credentials, or absolute private paths are included in the structured summary JSON.
