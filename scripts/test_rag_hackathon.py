"""Test RAG with Hackathon Vector DB stimulus — full output showing exactly what agents receive."""
import asyncio
import sys
sys.path.insert(0, "/mnt/g/WSL/projects/SimulateAI")

from src.rag.client import WebSearchClient
from src.rag.processor import extract_facts_with_llm
from src.rag.query_gen import generate_perspective_queries
from src.llm.client import UnifiedLLMClient
from config import DEFAULT_MODEL


STIMULUS = """A two-person team submits to a 48-hour hackathon: an open-source vector database written entirely in Rust, compiled to WebAssembly, running in-browser with claims of 8x faster cosine search than Pinecone for sub-1M-vector workloads. Demo loads in a single HTML file."""


async def test():
    search = WebSearchClient()
    llm = UnifiedLLMClient(model=DEFAULT_MODEL)

    output_lines = []

    def out(line=""):
        output_lines.append(line)
        print(line)

    out("# RAG Output — Hackathon Vector DB (Rust + WASM)")
    out()
    out("## Stimulus")
    out(f"> {STIMULUS}")
    out()

    # --- Step 1: Generate queries via LLM (same as real pipeline) ---
    # We simulate what the pipeline does by creating a mock schema
    class MockCluster:
        def __init__(self, cluster_id, description):
            self.cluster_id = cluster_id
            self.description = description

    class MockSchema:
        def __init__(self):
            self.scenario_name = "Hackathon: In-Browser Vector Database (Rust/WASM) claiming 8x Pinecone speed"
            self.scenario_description = (
                "A two-person team presents an open-source vector database written in Rust, "
                "compiled to WebAssembly, running entirely in-browser. Claims 8x faster cosine "
                "similarity search than Pinecone for sub-1M-vector workloads. Demo is a single HTML file."
            )
            self.linguistic_clusters = [
                MockCluster("hackathon_judge", "Technical judge evaluating feasibility, novelty, and benchmark validity of the WASM vector DB"),
                MockCluster("vc_scout", "Early-stage VC scout assessing commercial viability and market timing for browser-native AI infrastructure"),
                MockCluster("db_engineer", "Senior database/systems engineer skeptical of WASM performance claims vs native vector DBs"),
                MockCluster("indie_developer", "Solo developer excited about embedding vector search without server costs or vendor lock-in"),
            ]

    schema = MockSchema()

    out("## Step 1: LLM Query Generation")
    out()
    out("Using the same `generate_perspective_queries()` function as the real pipeline:")
    out()

    perspective_queries = await generate_perspective_queries(llm, schema)

    for cluster_id, queries in perspective_queries.items():
        out(f"- **{cluster_id}**")
        out(f"  - [SENTIMENT] `{queries[0]}`")
        if len(queries) > 1:
            out(f"  - [CONTEXT] `{queries[1]}`")
        out()

    # --- Step 2: Execute searches ---
    out("---")
    out()
    out("## Step 2: Search Execution + Fact Extraction")
    out()

    all_perspectives = {}

    for cluster_id, queries in perspective_queries.items():
        out(f"### Cluster: `{cluster_id}`")
        cluster_desc = next(c.description for c in schema.linguistic_clusters if c.cluster_id == cluster_id)
        out(f"*{cluster_desc}*")
        out()

        cluster_facts = []

        for qi, query in enumerate(queries):
            query_type = "SENTIMENT" if qi == 0 else "CONTEXT"
            is_sentiment = (qi == 0)

            out(f"#### [{query_type}] `{query}`")
            out()

            results = await search.search(query, max_results=5, allow_social=is_sentiment)
            # Delay between queries to avoid SearXNG engine rate limits
            await asyncio.sleep(2.5)

            if results:
                out(f"**{len(results)} results found:**")
                out()
                for i, r in enumerate(results, 1):
                    out(f"  {i}. [{r.score:.2f}] **{r.title[:80]}**")
                    out(f"     {r.url[:100]}")
                    content_preview = r.content[:150].replace("\n", " ") if r.content else "(no content)"
                    out(f"     > {content_preview}...")
                    out()

                # LLM extraction
                facts = await extract_facts_with_llm(
                    llm, results, query,
                    context=f"Scenario: {schema.scenario_name}. Role: {cluster_id} — {cluster_desc}",
                    max_facts=4,
                )
                out(f"**Extracted Facts:**")
                for i, f in enumerate(facts.facts, 1):
                    out(f"  {i}. {f}")
                    cluster_facts.append(f)
                out()
                if facts.citations:
                    out(f"**Sources:**")
                    for c in facts.citations:
                        out(f"  - [{c.title[:70]}]({c.url})")
                    out()
            else:
                out("  *(no results)*")
                out()

        all_perspectives[cluster_id] = cluster_facts
        out()

    # --- Step 3: Show EXACTLY what the Swarm Generator receives ---
    out("---")
    out("---")
    out()
    out("# EXACT PROMPT INJECTION: What Gets Fed to the Swarm Agent Generator")
    out()
    out("The following text block is injected verbatim into the persona-generation prompt.")
    out("This is the `swarm_rag_perspectives` variable that shapes each agent's worldview:")
    out()
    out("```")
    out()
    out("STAKEHOLDER PERSPECTIVES (real-world attitudes — use to shape each agent's worldview):")
    out()
    for cluster_id, facts in all_perspectives.items():
        cluster_desc = next(c.description for c in schema.linguistic_clusters if c.cluster_id == cluster_id)
        if facts:
            out(f'  For cluster "{cluster_id}" ({cluster_desc}):')
            for fact in facts:
                out(f"    - {fact}")
            out()
    out("Use these real-world perspectives to shape each agent's memory_vectors and attitudes.")
    out("Agents should reflect the genuine sentiments and worldview of their stakeholder group.")
    out("Do NOT copy verbatim — synthesize into character-defining beliefs.")
    out()
    out("```")
    out()

    # --- Step 4: Show crisis injection format ---
    out("---")
    out()
    out("# CRISIS INJECTION FORMAT (Round 3)")
    out()
    out("After Round 2 debate, a crisis-specific RAG search runs using the transcript.")
    out("For this scenario, likely crisis queries might be:")
    out("  - `\"vector database WASM security vulnerability browser\"`")
    out("  - `\"open source database project abandoned maintainer burnout\"`")
    out()
    out("The extracted facts appear in the crisis prompt as:")
    out()
    out("```")
    out("REAL-WORLD PRECEDENTS (use to ground the crisis in actual events):")
    out("- [fact 1 from crisis search — e.g. a real WASM security incident]")
    out("- [fact 2 from crisis search — e.g. a real OSS abandonment case]")
    out()
    out("Base your crisis event on a real or plausible variation of these precedents.")
    out("```")

    await search.close()

    # Write to markdown
    outpath = "/mnt/g/WSL/projects/SimulateAI/graphify-out/rag_output_hackathon_vectordb.md"
    with open(outpath, "w") as f:
        f.write("\n".join(output_lines))
    print(f"\n\n--- Written to {outpath} ---")


if __name__ == "__main__":
    asyncio.run(test())
