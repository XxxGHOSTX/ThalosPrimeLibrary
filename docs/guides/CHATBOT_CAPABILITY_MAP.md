# Single Chatbot Capability Map

## North Star

One default chatbot experience with optional advanced directions.

## Modes

| Mode | Goal | Primary Internal Capabilities | Output Requirement |
|---|---|---|---|
| `standard` | Fast, grounded answer | retrieval + coherence scoring + evidence packaging | concise answer + evidence + confidence |
| `deep_research` | Multi-step synthesis and verification | multi-source retrieval, contradiction checks, synthesis, benchmark scoring | expanded answer + citation/evidence chain + uncertainty |
| `build` | Autonomous repository engineering | planning + constraints + execution + test/lint reporting | plan/actions/tests/outcomes + reproducibility metadata |
| `image` | User-requested image capability | prompt transformation + generator integration + provenance tagging | image result metadata + generation parameters + constraints |
| `diagnostics` | Explain runtime behavior | lifecycle/worker/cache/status/audit surfaces | health report + anomalies + corrective actions |

## Unified Response Schema (All Modes)

```json
{
  "mode": "standard|deep_research|build|image|diagnostics",
  "answer": "string",
  "evidence": [
    {
      "id": "string",
      "kind": "source|artifact|test|run|log",
      "reference": "string",
      "confidence": 0.0
    }
  ],
  "confidence": {
    "overall": 0.0,
    "level": "low|medium|high"
  },
  "actions": [
    {
      "step": 1,
      "action": "string",
      "result": "string"
    }
  ],
  "reproducibility": {
    "seed": 0,
    "config_hash": "string",
    "checkpoint_id": "string",
    "version": "string"
  }
}
```

## UX Contract

- Default mode is `standard`.
- Mode switching is explicit, user-visible, and reversible.
- Same output shape in all modes to keep UI simple and predictable.

## Capability Governance

- New capabilities must register as a mode extension or internal tool under an existing mode.
- No capability may bypass evidence and reproducibility fields.
