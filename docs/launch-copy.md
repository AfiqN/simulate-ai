# SimulateAI — Launch Copy

## Product Hunt

**Tagline (60 chars):**
Stress-test any decision with AI personas before you commit

**Description:**
SimulateAI runs multi-agent simulations on your decisions. Describe a scenario — product launch, policy change, strategic bet — and AI personas debate it from every angle across 3 rounds: initial perception, adversarial debate, and crisis stress-test.

You get back: coalition maps, blind spots, failure modes, and a diagnostic report — in minutes, not months of stakeholder meetings.

**Key features:**
- 🎭 Diverse AI personas with realistic cognitive profiles
- ⚔️ Adversarial mode that actively tries to disprove your assumptions
- 📊 Quantified consensus, faction analysis, and swing-vote identification
- 🔓 Fully open-source — bring your own API key, run unlimited simulations

**First Comment (founder):**
Hey PH! 👋 I built SimulateAI because I was tired of pitching ideas and only hearing "sounds good" — then watching them fail for reasons someone could have predicted.

This tool creates a room of AI stakeholders who actually disagree. They form coalitions, challenge claims with evidence, and react to crisis scenarios. The output isn't "AI said yes/no" — it's a map of WHO would resist, WHY, and what breaks under stress.

It's free and open-source. Bring your own API key (OpenAI, Anthropic, or Google) and run as many simulations as you want.

Would love feedback on what scenarios you'd want to stress-test!

---

## Reddit Posts

### r/SideProject

**Title:** I built an open-source tool that stress-tests your decisions with AI debate simulations

**Body:**
I kept pitching ideas at work and getting polite nods — then watching them fail for reasons that were predictable in hindsight.

So I built SimulateAI: describe any decision (product launch, policy change, hiring strategy) and it spawns AI personas who debate it across 3 rounds — perception, adversarial challenge, and crisis stress-test.

What you get back:
- Who supports vs. resists your idea (and why)
- Blind spots you missed
- What breaks under stress
- A full diagnostic report with evidence

It's free, open-source, and you bring your own API key (OpenAI/Anthropic/Google).

Tech stack: Python backend (multi-agent pipeline), React frontend, WebSocket for real-time progress.

Live: https://simulate-ai-production.up.railway.app
GitHub: https://github.com/AfiqN/simulate-ai

Would love to hear what decisions you'd want to simulate!

---

### r/artificial

**Title:** Multi-agent AI simulation for decision stress-testing — open source

**Body:**
I've been experimenting with multi-agent systems and built a simulation engine that models how different stakeholder personas would react to a decision.

The pipeline:
1. Schema generation — AI designs the scenario architecture (agents, dimensions, actions)
2. Swarm creation — generates diverse personas with cognitive profiles
3. Round 1 (Perception) — agents form initial positions independently
4. Round 2 (Debate) — adversarial pairing, agents challenge each other with evidence
5. Round 3 (Crisis) — a stress event is injected, agents must adapt
6. Synthesis — faction analysis, consensus measurement, blind spot identification

Interesting findings from testing:
- Adversarial mode (where a "devil's advocate" actively tries to disprove claims) catches ~40% more failure modes than collaborative mode
- The crisis round is where the real insights emerge — coalitions that held during debate often fracture under stress
- Historical precedent injection (feeding real-world analogues) significantly improves prediction quality

It's open-source and supports OpenAI, Anthropic, and Google models.

GitHub: https://github.com/AfiqN/simulate-ai
Try it: https://simulate-ai-production.up.railway.app

---

## Twitter/X Thread

**Tweet 1 (hook):**
I built a tool that creates a room of AI stakeholders who actually disagree with you.

Not "AI said yes." A full debate simulation with coalitions, evidence, and stress-tests.

Open-source, free to use. Here's what it does 🧵

**Tweet 2:**
The problem: You have an idea. You pitch it. Everyone says "sounds good."

6 months later it fails for reasons someone could have predicted — but nobody wanted to be the skeptic.

SimulateAI is that skeptic. It spawns 5-7 AI personas and makes them debate your idea across 3 rounds.

**Tweet 3:**
Round 1 — Perception
Each agent forms an independent position. No groupthink.

Round 2 — Debate
Agents challenge each other with evidence. Adversarial mode assigns a "devil's advocate" who actively tries to disprove your strongest assumptions.

**Tweet 4:**
Round 3 — Crisis
A stress event gets injected. Market crash. Competitor move. Regulation change.

This is where coalitions fracture and the real blind spots emerge. The agents who supported you in calm conditions might flip under pressure.

**Tweet 5:**
What you get back:
→ Coalition map (who aligns with whom)
→ Blind spots identified
→ Failure modes ranked by severity
→ Swing votes — agents who could go either way
→ Full diagnostic report

All in ~5 minutes.

**Tweet 6:**
It's open-source and supports:
- OpenAI (GPT-4o)
- Anthropic (Claude)
- Google (Gemini)

Bring your own API key, run unlimited simulations.

Try it: simulate-ai-production.up.railway.app
GitHub: github.com/AfiqN/simulate-ai

What decision would you stress-test first?

---

## LinkedIn Post

**Post:**
I spent the last few months building something I wish existed years ago.

How many times have you presented a strategy and heard "sounds good" — only to watch it fail for reasons that were, in hindsight, completely predictable?

SimulateAI creates a virtual room of AI stakeholders who are programmed to disagree. They debate your decisions across three rounds: initial perception, adversarial challenge, and crisis stress-test.

The output isn't a simple yes/no. It's:
• A coalition map showing who supports and resists your idea
• Blind spots you couldn't see from your perspective
• Failure modes ranked by likelihood and severity
• A diagnostic report with evidence for every claim

Use cases I've seen work well:
→ Product launches: "Will users adopt? Which stakeholders will resist?"
→ Policy decisions: "What are the unintended consequences?"
→ Strategic bets: "What breaks under competitive pressure?"

It's open-source and free to use. No vendor lock-in — bring your own API key from OpenAI, Anthropic, or Google.

Try it: https://simulate-ai-production.up.railway.app
Star on GitHub: https://github.com/AfiqN/simulate-ai

What decision would you stress-test?

#AI #DecisionMaking #OpenSource #MultiAgentSystems
