# Methodology

## Purpose

SimulateAI is a structured decision stress-test. It explores how generated stakeholder personas could react under explicit assumptions. It does not predict real people, estimate real-world probabilities, or replace domain experts.

## Schema-first simulation

An architect model converts the stimulus into a scenario-specific schema: available actions, state vocabulary, resources, evaluation dimensions, and terminal conditions. Agents then operate against that shared schema rather than an application-wide hardcoded vocabulary.

## Persona swarm

The swarm is generated to vary archetype, priorities, risk tolerance, aggressiveness, rationality, resources, constraints, and linguistic cluster. Custom stakeholders can be supplied. Optional RAG adds external perspectives and historical context; retrieved text is supporting context, not verified ground truth.

## Rounds

1. **Perception:** agents independently form an action, dimensional utility vector, and rationale.
2. **Debate:** agents observe competing positions and revise or defend their stance. Adversarial mode instead extracts claims, assigns challenges, and records surviving/defeated claims.
3. **Crisis:** a generated or supplied shock tests whether actions and coalitions remain stable.
4. **Reconciliation (deep collaborative mode):** agents attempt compromise while preserving minority analysis.

Quick depth runs initial assessment plus crisis; Standard runs perception/debate/crisis; Deep adds reconciliation.

## Deterministic verdict

The report compiler—not the narrative LLM—assigns the verdict from computed metrics. Current thresholds are:

- **Resilient:** stability score at least `0.6`, utility drift at least `-0.2`, and terminal-action delta at most `0.2`.
- **Fragile:** stability below `0.4`, utility drift below `-0.4`, or terminal-action delta above `0.4`.
- **Moderate:** outcomes between those boundaries.
- **Indeterminate:** insufficient comparable rounds.

The narrative report explains evidence but cannot override the deterministic classification.

## Interpretation

Use results to identify assumptions, dissent, coalition fragility, and follow-up questions. Do not interpret a score as calibrated probability or validation that a decision is safe. Model/provider changes can alter schemas, personas, rationales, and downstream metrics. For consequential decisions, run multiple configurations, inspect primary evidence, and consult qualified humans.

## Reproducibility

Serialization and metric computation are deterministic for a fixed completed simulation object. LLM generation is not fully reproducible across providers or time: hosted models, sampling, search results, and provider implementations can change. SimulateAI therefore preserves complete canonical snapshots rather than claiming deterministic regeneration.
