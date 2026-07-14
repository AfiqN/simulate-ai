# SimulateAI Control Test — Data Contamination Analysis

**Generated:** 2026-07-13T17:22:26.987756
**Model:** `claude-sonnet-4.6`

---

## Methodology

Two controls per case to isolate pipeline value from model recall:

| Mode | What it tests |
|------|--------------|
| **Direct** | Same stimulus → single LLM call (no pipeline). Measures raw model prediction ability. |
| **Decontaminated** | Identifying names/dates stripped → single LLM call. Measures pure structural reasoning. |

**Key Metrics:**
- `Pipeline Value-Add` = pipeline_score - direct_score (positive = pipeline helps)
- `Contamination Signal` = direct_score - decontaminated_score (positive = model recognizes event)

---

## Results

| Case | Direct | Decontaminated | Contam. Signal | Pipeline | Value-Add |
|------|--------|----------------|----------------|----------|-----------|
| crowdstrike_outage | 8.9 | 8.9 | +0.0 | 6.2 | -2.7 |
| gamestop_squeeze | 9.4 | 9.2 | +0.2 | N/A | N/A |
| openai_board_crisis | 7.9 | 7.9 | +0.0 | 7.1 | -0.8 |
| svb_collapse | 9.5 | 9.5 | +0.0 | 8.7 | -0.8 |
| tiktok_ban | 7.9 | 7.9 | -0.0 | N/A | N/A |
| **Average** | **8.8** | **8.7** | **+0.0** | | |

---

## Interpretation

**LOW contamination.** The model appears to reason primarily from structural dynamics, not from recall of specific events.

**Pipeline Value-Add: -1.4**

The multi-agent pipeline adds **minimal** value over direct prompting for these cases.

---

## Per-Dimension Breakdown

| Case | Mode | Verdict | Behavior | Risk | Resilience |
|------|------|---------|----------|------|------------|
| crowdstrike_outage | Direct | 9.0 | 8.0 | 9.0 | 10.0 |
| crowdstrike_outage | Decontam | 9.0 | 8.0 | 9.0 | 10.0 |
| gamestop_squeeze | Direct | 9.0 | 9.0 | 10.0 | 10.0 |
| gamestop_squeeze | Decontam | 9.0 | 9.0 | 9.0 | 10.0 |
| openai_board_crisis | Direct | 9.0 | 8.0 | 9.0 | 5.0 |
| openai_board_crisis | Decontam | 9.0 | 8.0 | 9.0 | 5.0 |
| svb_collapse | Direct | 10.0 | 9.0 | 9.0 | 10.0 |
| svb_collapse | Decontam | 10.0 | 9.0 | 9.0 | 10.0 |
| tiktok_ban | Direct | 8.0 | 9.0 | 9.0 | 5.0 |
| tiktok_ban | Decontam | 9.0 | 8.0 | 9.0 | 5.0 |
