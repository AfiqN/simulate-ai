"""Test RAG with medical AI startup stimulus."""
import asyncio
import sys
sys.path.insert(0, "/mnt/g/WSL/projects/SimulateAI")

from src.rag.client import WebSearchClient
from src.rag.processor import extract_facts_with_llm, process_search_results
from src.rag.query_gen import generate_perspective_queries
from src.llm.client import UnifiedLLMClient


STIMULUS = """A YC-backed startup with $2M seed funding launches an AI-powered medical transcription tool for Southeast Asian clinics. The tool converts doctor-patient conversations in Bahasa Indonesia and Malay into structured SOAP notes with ICD-10 codes, reducing documentation time from 15 minutes to 90 seconds. They already have 50 paying clinics in Jakarta, 98% accuracy on internal benchmarks, BAA-compliant infrastructure, and letters of intent from 3 hospital chains. The team includes a former Halodoc VP of Engineering and a practicing physician."""


async def test():
    search = WebSearchClient()
    llm = UnifiedLLMClient()

    print("=" * 70)
    print("STIMULUS (abbreviated):")
    print(f"  {STIMULUS[:100]}...")
    print("=" * 70)

    # Simulate dual-query approach (sentiment + context per role)
    roles = [
        {
            "archetype": "VC Investor",
            "context": "Evaluating Series A potential, market size, competitive moat",
            "queries": [
                "healthtech startup founders frustrations fundraising Southeast Asia investors skeptical",
                "AI medical transcription startup market size Southeast Asia 2024",
            ],
        },
        {
            "archetype": "Hospital CTO",
            "context": "Assessing integration risk, data security, vendor lock-in",
            "queries": [
                "hospital IT managers complaints AI vendor integration EHR system pain points",
                "hospital EHR integration AI tools challenges Indonesia regulation",
            ],
        },
        {
            "archetype": "Indonesian Health Regulator",
            "context": "Evaluating compliance with health data laws, patient safety",
            "queries": [
                "Indonesian doctors opinions AI clinical documentation concerns patient trust",
                "Indonesia health AI regulation Kemenkes digital health policy SATUSEHAT 2024",
            ],
        },
    ]

    for role in roles:
        print(f"\n{'─'*70}")
        print(f"ROLE: {role['archetype']}")
        print(f"CONTEXT: {role['context']}")
        print(f"{'─'*70}")

        queries = role["queries"]
        print(f"\n  Queries:")
        print(f"    [SENTIMENT] {queries[0]}")
        print(f"    [CONTEXT]   {queries[1]}")

        # Search
        all_results = []
        for q in queries:
            results = await search.search(q, max_results=3)
            all_results.extend(results)
        print(f"\n  Total raw results: {len(all_results)}")

        if all_results:
            # LLM extraction
            facts = await extract_facts_with_llm(
                llm, all_results, " | ".join(queries),
                context=f"Role: {role['archetype']}. {role['context']}",
                max_facts=4,
            )
            print(f"\n  Extracted facts ({len(facts.facts)}):")
            for i, f in enumerate(facts.facts, 1):
                print(f"    {i}. {f}")
            print(f"\n  Citations ({len(facts.citations)}):")
            for c in facts.citations:
                print(f"    - {c.title[:60]} ({c.url[:50]}...)")
        else:
            print("  No results found.")

    await search.close()


if __name__ == "__main__":
    asyncio.run(test())
