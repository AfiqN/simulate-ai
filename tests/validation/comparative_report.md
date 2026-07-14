# SimulateAI Comparative Validation — Collaborative vs Adversarial

**Generated:** 2026-07-14T01:19:10.609830
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
| crowdstrike_outage | 5.7 | 4.9 | -0.8 | -1.0 | 8.4 | 100% |
| gamestop_squeeze | 5.7 | 6.3 | +0.6 | +1.0 | 8.2 | 95% |
| openai_board_crisis | 5.8 | 5.5 | -0.3 | +0.0 | 7.9 | 100% |
| svb_collapse | 5.1 | 7.1 | +2.1 | +1.0 | 7.9 | 100% |
| tiktok_ban | 6.0 | 7.1 | +1.0 | +0.0 | 8.4 | 92% |
| **Average** | **5.7** | **6.2** | **+0.5** | **+0.2** | **8.1** | |

---

## Adversarial Quality Breakdown

| Case | Claim Rel. | Attack Spec. | Defense Rigor | Survival Plaus. | Insight Δ |
|------|-----------|-------------|--------------|-----------------|-----------|
| crowdstrike_outage | 9.0 | 9.0 | 8.0 | 7.0 | 9.0 |
| gamestop_squeeze | 8.0 | 9.0 | 8.0 | 7.0 | 9.0 |
| openai_board_crisis | 8.0 | 9.0 | 8.0 | 6.0 | 8.0 |
| svb_collapse | 8.0 | 9.0 | 8.0 | 6.0 | 8.0 |
| tiktok_ban | 8.0 | 9.0 | 8.0 | 8.0 | 9.0 |

---

## Interpretation

**Adversarial mode improves prediction accuracy.** Stress-testing claims leads to better-calibrated verdicts.

**Adversarial debate quality is high** (8.1/10). Claims, attacks, and defenses are substantive and relevant.
