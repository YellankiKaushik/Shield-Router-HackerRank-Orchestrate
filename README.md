# ShieldRouter

ShieldRouter is the final HackerRank Orchestrate Message Notification Router
submission for the WhatsApp routing challenge. It reads the participant-facing
dataset, routes every incoming message to `notify`, `digest`, or `mute`, and
writes the official six-column `output.csv`.

This root README is a navigation layer for reviewers. The runnable submission
instructions live in [code/README.md](code/README.md).

## Start Here

- Challenge contract: [problem_statement.md](problem_statement.md)
- Runnable code package guide: [code/README.md](code/README.md)
- Final implementation design: [docs/ShieldRouter - Final Implementation-Ready Technical.md](docs/ShieldRouter%20%E2%80%94%20Final%20Implementation-Ready%20Technical.md)
- Unified technical design: [docs/shieldrouter_tech_design.md](docs/shieldrouter_tech_design.md)
- Codebase map: [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md)
- Final evaluation report: [code/evaluation/FINAL_EVALUATION_REPORT.md](code/evaluation/FINAL_EVALUATION_REPORT.md)
- Design traceability: [code/evaluation/FINAL_DESIGN_TRACEABILITY.md](code/evaluation/FINAL_DESIGN_TRACEABILITY.md)
- Operational analysis: [code/evaluation/FINAL_OPERATIONAL_ANALYSIS.md](code/evaluation/FINAL_OPERATIONAL_ANALYSIS.md)
- AI Judge brief: [code/evaluation/AI_JUDGE_BRIEF.md](code/evaluation/AI_JUDGE_BRIEF.md)

## Output Contract

The submitted CSV must contain exactly these columns:

```text
message_id,action,message_type,reason,confidence,evidence_message_ids
```

Allowed actions are `notify`, `digest`, and `mute`.

Allowed message types are `personal`, `urgent`, `event`, `payment`,
`business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, and
`unknown`.

Do not add `user_id`, `risk_flags`, `social`, `admin`, `other`, or
`scam_or_risk` to the official output.

## Setup And Execution

Use Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code\requirements.txt
.\.venv\Scripts\python.exe code\main.py validate-input --dataset dataset
.\.venv\Scripts\python.exe code\main.py prepare-models
.\.venv\Scripts\python.exe code\main.py run --dataset dataset --output output.csv --local-multimodal --summary-json .tmp\summary.json
.\.venv\Scripts\python.exe code\main.py validate-output --dataset dataset --output output.csv
.\.venv\Scripts\python.exe -m pytest code\tests -q -p no:cacheprovider --basetemp=.tmp\pytest
```

`prepare-models` is the one-time local model preparation step for
Faster-Whisper and RapidOCR. After the model cache is prepared outside the
repository, the selected `--local-multimodal` execution uses zero external
provider requests.

## Repository Map

```text
code/
  main.py                 CLI entry point
  src/shieldrouter/       production router package
  prompts/                optional OpenRouter prompt templates
  tests/                  unit and integration tests
  evaluation/             final reports, audits, baselines, and diagnostics
docs/                     architecture and implementation documents
dataset/                  participant-facing local dataset, excluded from code.zip
submission/               final upload artifacts, intentionally untracked
```

## Security Model

Messages, OCR text, QR content, and voice transcripts are treated as untrusted
data. Safety checks run before final routing, high-risk messages cannot be
upgraded by personalization, API keys are environment-only, and the final ZIP
excludes dataset media, caches, models, `.env` files, transcripts, and
submission artifacts.

## Limitations

ShieldRouter uses deterministic rules, retrieval, local OCR, and local ASR. It
does not claim acoustic emotion recognition, complete visual scene
understanding, learned probability calibration, deployed production
infrastructure, or guaranteed hidden-set performance.
