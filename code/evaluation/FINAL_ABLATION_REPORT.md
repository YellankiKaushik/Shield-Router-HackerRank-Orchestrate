# Final Safety Ablation Report

This is evaluation-only. Safety-disabled routing is not exposed as a production `run` option.

| Mode | Action acc | Action macro F1 | Type acc | Type macro F1 | Scam P/R | Notify P/R | Runtime | Provider calls | Fallback rate |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|
| Safety enabled deterministic sample | 0.9333 | 0.9351 | 0.9 | 0.8955 | 1.0/1.0 | 1.0/0.8889 | 0.0361 | 0 | 0.0 |
| Safety disabled ablation sample | 0.7667 | 0.7487 | 0.7333 | 0.6111 | 0.0/0.0 | 0.8889/0.8889 | 0.0319 | 0 | 0.0 |
| Offline text/context | 0.9333 | 0.9351 | 0.9 | 0.8955 | 1.0/1.0 | 1.0/0.8889 | n/a | 0 | 0 |
| Local voice | 0.9667 | 0.968 | 0.9333 | 0.9209 | 1.0/1.0 | 1.0/1.0 | 0 | 0 | 0 |
| Local multimodal selected | 1.0 | 1.0 | 1.0 | 1.0 | 1.0/1.0 | 1.0/1.0 | 0 | 0 | 0 |

Key observations:

- Safety enabled sample false-positive scams: [].
- Safety enabled sample false-negative urgent cases: ['sample_msg_042'].
- Safety disabled sample false-positive scams: [].
- Safety disabled sample false-negative urgent cases: ['sample_msg_042'].
- Optional OpenRouter hybrid artifacts are historical/advisory only and do not represent the selected submission mode.
- Perfect labeled-sample metrics do not guarantee hidden-set performance.
