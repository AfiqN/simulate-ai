# SimulateAI — Roadmap to Production

> Domain-agnostic multi-agent simulation for any decision — bisnis, kebijakan, personal, komunitas.
> Goal: output yang cukup rigorous untuk jadi salah satu input decision-making serius.

---

## Current State (v0.1 — Local PoC)

✅ Schema-first architecture (domain-agnostic)  
✅ 3-round pipeline: perceive → debate → crisis  
✅ Quantitative resilience metrics (deterministic, bukan LLM-hallucinated)  
✅ Action-coverage-backward persona design  
✅ RAG perspective injection per-role  
✅ Web frontend + live progress  
✅ Language-aware reports (Indonesian stimulus → Indonesian report)  

### Known Gaps (from internal audit)

1. Flat utility model — single scalar [-1,1] collapses multi-dimensional evaluation
2. No observable reasoning chain — agent output cuma 1 kalimat reflection
3. No quantitative report output — final report 100% LLM prose
4. One-shot everything — no iterative refinement, no user validation
5. Shallow persona differentiation — 3 float + 2 memory
6. No game-theoretic structure — no formal payoff/consequence model
7. No reproducibility — same stimulus = different result, no variance measurement

---

## Phase 1 — Credibility Layer

**Goal:** Output yang data-driven, auditable, dan adjustable depth.

### 1.1 Analysis Depth Tiers

Tambah parameter `depth` ke pipeline: `quick | standard | deep`

| Aspect | Quick | Standard | Deep |
|--------|-------|----------|------|
| Rounds | 2 (perceive + crisis, skip debate) | 3 (full) | 3 + follow-up reconciliation round |
| Agents | 3–5 | 5–10 | 10–20 |
| Reasoning | Concise (1-2 sentences) | Standard reflection | Full chain-of-thought per dimension |
| Re-runs | 1x | 1x | 3–5x (for confidence intervals) |
| Report | Verdict + 1-paragraph summary | Full 6-section report | Full report + confidence intervals + sensitivity + minority report |
| Time estimate | 1–3 min | 5–10 min | 15–40 min |

**Use cases:**
- Quick → brainstorming, screening, sanity check
- Standard → most decisions, presentations
- Deep → high-stakes strategy, investment committee, policy submission

**UI:** Dropdown di form — `Depth: [Quick ▾] [Standard ▾] [Deep ▾]`

### 1.2 Multi-Dimensional Utility

Replace scalar utility → vector, auto-generated dari stimulus oleh Architect.

```
# Sekarang:
utility: 0.65

# Nanti:
utility: {
  financial_viability: 0.8,
  regulatory_risk: -0.3,
  social_impact: 0.6,
  implementation_feasibility: 0.4
}
```

Dimensi TIDAK hardcoded — Architect generate dari stimulus:
- Bisnis pitch → `{market_fit, financial_return, competitive_risk, execution_feasibility}`
- Kebijakan publik → `{equity, cost_efficiency, political_feasibility, long_term_impact}`
- Personal decision → `{financial_security, happiness, growth_potential, relationship_impact}`
- Teknis → `{performance, maintainability, adoption_cost, risk}`

Resilience metrics juga jadi per-dimensi: "stability dropped on financial axis but held on social impact."

### 1.3 Structured Reasoning Chain

Force chain-of-thought per agent, stored as structured array:

```json
{
  "reasoning_chain": [
    {"dimension": "financial_viability", "assessment": "Strong unit economics at scale, but requires 18mo runway", "score": 0.7},
    {"dimension": "regulatory_risk", "assessment": "Current framework unclear, could face retroactive enforcement", "score": -0.4},
    {"dimension": "social_impact", "assessment": "Addresses real pain point for underbanked communities", "score": 0.8}
  ],
  "key_uncertainty": "Regulatory stance post-election is unknowable",
  "decision": "INVEST",
  "confidence": 0.6
}
```

Ini memberi:
- Audit trail per agent per dimensi
- Ability to ask "why did X flip on Y dimension?"
- Confidence score per decision (bukan binary commit)

### 1.4 Quantitative Report Section

Sebelum LLM menulis prose, compute dan inject:

- **Vote tally per action** — "7/10 INVEST, 2 OPPOSE, 1 ABSTAIN"
- **Per-dimension score distributions** — mean, stdev, min/max across agents
- **State transition matrix** — who shifted from what to what between rounds
- **Swing analysis** — which agents changed action + which dimension drove the flip
- **Consensus index** — Herfindahl-like measure of action concentration
- **Net confidence** — average agent confidence weighted by utility magnitude

Report LLM menerima angka-angka ini dan HARUS reference them, bukan invent own statistics.

---

## Phase 2 — Depth Layer

**Goal:** Richer simulation dynamics, reproducibility, user control.

### 2.1 Schema Validation Loop

Architect generates draft schema → presented to user → user can:
- Approve as-is
- Add/remove actions
- Adjust evaluation dimensions
- Add domain context/constraints
- Lock → proceed

(Di API mode: optional — kalau tidak di-validate, auto-proceed like sekarang)

### 2.2 Richer Persona Model

Expand dari 3 floats ke:
- **Decision framework** — what this agent prioritizes (e.g. "loss-averse, values precedent over innovation")
- **Knowledge base** — what domain-specific things this agent knows/believes
- **Constraints** — what this agent CANNOT do or accept (red lines)
- **Influence weight** — not all voices equal (CEO vs intern, regulator vs commentator)
- **Backstory snippet** — 2-3 sentences grounding the persona in specific experience

### 2.3 Multi-Round Adversary Evolution

- Re-pair after each round based on emerging fault lines (not just Round 1 snapshot)
- Allow 2-on-1 or panel debates in Deep mode
- Track alliance formation/dissolution across rounds

### 2.4 Sensitivity Analysis (Deep mode)

- Auto re-run 3-5x with temperature variation
- Report: "Verdict = Resilient in 4/5 runs, Moderate in 1/5"
- Identify which agents are swing voters (changed verdict across runs)
- Identify which dimensions are most sensitive

### 2.5 Follow-up Reconciliation Round (Deep mode)

After Round 3 crisis, add Round 4:
- Show agents the aggregate results ("7/10 of you chose INVEST")
- Ask: "Given this collective outcome, do you revise your position?"
- Measures: herding effect, conviction stability, minority resilience

---

## Phase 3 — Enterprise Polish

**Goal:** Professional deliverable, integrable, scalable.

### 3.1 Structured Output Format

Alongside markdown report, emit:
- JSON summary with all metrics, scores, distributions
- Chart-ready data (utility trajectories, faction pie, state sankey)
- PDF export option
- Comparison mode: run A vs run B

### 3.2 Custom Stakeholder Injection

User can define specific personas:
- "Simulate our CFO (conservative, focused on cash flow)"
- "Simulate the regulator (strict interpretation, risk-averse)"
- Mix with auto-generated personas to fill gaps

### 3.3 Conditional Dynamics

Schema can define triggers:
- "If 3+ agents OPPOSE, action COMPROMISE becomes available"
- "If crisis hits financial dimension, resource depletion doubles"
- Game-theoretic payoff modifications based on collective state

### 3.4 Historical Context

- Compare current run to past simulations with similar stimuli
- Track decision accuracy over time (if user marks actual outcomes later)
- "Your previous 5 simulations about fintech regulation: 3 Resilient, 2 Moderate"

### 3.5 API-First + Webhooks

- Clean REST API for integration with Notion, Slack, internal tools
- Webhook on completion
- Batch mode: submit 10 stimuli, get 10 reports
- Rate-limited public tier + unlimited self-hosted

---

## Implementation Priority (within Phase 1)

```
1. Depth tiers (quick/standard/deep)     ← controls everything else
2. Multi-dimensional utility              ← highest impact on output quality
3. Structured reasoning chain             ← makes output auditable
4. Quantitative report pre-computation    ← makes report data-driven
```

Each builds on the previous. Depth tier determines how much reasoning/re-running happens. Multi-dim utility gives structured data. Reasoning chain makes it transparent. Quant report presents it professionally.

---

## Non-Goals (tetap out of scope)

- Real-time collaboration / multiplayer editing
- Agent training / fine-tuning
- Autonomous decision execution (we inform, not decide)
- Industry-specific templates (schema architect handles any domain)
- Mobile app (web-first, responsive later)
