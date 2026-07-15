# SimulateAI Comparative Validation — Collaborative vs Adversarial

**Generated:** 2026-07-14T23:36:48.557503
**Model:** `claude-sonnet-4.6`

---

## Methodology

Each historical case is run through both modes with identical parameters:
- 8 agents, concurrency 3, standard depth, no RAG
- Scored by an LLM judge against ground truth (same dimensions)
- Adversarial mode additionally scored on debate quality

---

## Results

| Case | Collaborative | Adversarial | Δ Accuracy | Δ Risk ID | Adv. Quality | Survival |
|------|--------------|-------------|------------|-----------|--------------|----------|
| crowdstrike_outage | 5.3 | 6.3 | +1.0 | +1.0 | 8.4 | 79% |
| gamestop_squeeze | 5.4 | 5.4 | +0.0 | +0.0 | 8.6 | 53% |
| openai_board_crisis | 5.1 | 6.5 | +1.5 | +1.0 | 7.7 | 59% |
| svb_collapse | 7.3 | 8.9 | +1.6 | +0.0 | 8.6 | 77% |
| tiktok_ban | 5.1 | 5.5 | +0.5 | +0.0 | 8.1 | 46% |
| **Average** | **5.6** | **6.5** | **+0.9** | **+0.4** | **8.3** | |

---

## Adversarial Quality Breakdown

| Case | Claim Rel. | Attack Spec. | Defense Rigor | Survival Plaus. | Insight Δ |
|------|-----------|-------------|--------------|-----------------|-----------|
| crowdstrike_outage | 9.0 | 9.0 | 8.0 | 8.0 | 8.0 |
| gamestop_squeeze | 9.0 | 9.0 | 8.0 | 8.0 | 9.0 |
| openai_board_crisis | 8.0 | 9.0 | 8.0 | 6.0 | 7.0 |
| svb_collapse | 9.0 | 9.0 | 8.0 | 8.0 | 9.0 |
| tiktok_ban | 8.0 | 9.0 | 8.0 | 7.0 | 8.0 |

---

## Interpretation

**Adversarial mode improves prediction accuracy.** Stress-testing claims leads to better-calibrated verdicts.

**Adversarial debate quality is high** (8.3/10). Claims, attacks, and defenses are substantive and relevant.
