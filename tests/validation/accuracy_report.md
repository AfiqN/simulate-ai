# SimulateAI Validation Report — Hindsight Testing

**Generated:** 2026-07-13T16:02:13.546049
**Model:** `claude-sonnet-4.6`
**Runs per case:** 1

---

## Overall Results

| Metric | Value |
|--------|-------|
| Overall Score | **7.32** / 10 |
| Grade | **Moderate** |
| Cases Evaluated | 3 |
| Successful Runs | 3 / 3 |

### Grading Scale

| Grade | Threshold |
|-------|-----------|
| Strong | >= 7.5 |
| Moderate | >= 5.5 |
| Weak | >= 3.5 |
| Fail | < 3.5 |

---

## Per-Case Breakdown

| Case | Domain | Median Score | Verdict | Behavior | Risks | Resilience |
|------|--------|-------------|---------|----------|-------|------------|
| CrowdStrike Global IT Outage | tech | **6.2** | 6.0 | 7.0 | 8.0 | 3.0 |
| OpenAI Board Crisis / Sam Altman Firing | tech_corporate | **7.1** | 7.0 | 8.0 | 8.0 | 5.0 |
| Silicon Valley Bank Collapse | finance | **8.7** | 9.0 | 8.0 | 8.0 | 10.0 |

---

## Per-Domain Breakdown

| Domain | Avg Score | Cases |
|--------|-----------|-------|
| finance | 8.70 | 1 |
| tech_corporate | 7.10 | 1 |
| tech | 6.15 | 1 |

---

## Dimension Weights

| Dimension | Weight | Description |
|-----------|--------|-------------|
| verdict_match | 0.30 | Does simulation conclusion match reality? |
| behavioral_fidelity | 0.25 | Do agent behaviors match real-world actors? |
| risk_identification | 0.25 | Were actual risks identified? |
| resilience_accuracy | 0.20 | Was Fragile/Moderate/Resilient correct? |
