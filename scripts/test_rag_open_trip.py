"""Test RAG with Open Trip Booking Platform stimulus."""
import asyncio
import sys
sys.path.insert(0, "/mnt/g/WSL/projects/SimulateAI")

from src.rag.client import WebSearchClient
from src.rag.processor import extract_facts_with_llm
from src.rag.query_gen import generate_perspective_queries
from src.llm.client import UnifiedLLMClient
from config import DEFAULT_MODEL


STIMULUS = """Open Trip Booking Platform — Proposal Bisnis

Ringkasan Eksekutif: Open Trip adalah platform digital multi-tenant yang menghubungkan penyelenggara trip petualangan (gunung, laut, alam) dengan calon peserta. Platform ini memungkinkan banyak organizer mendaftarkan bisnisnya, mengelola trip, jadwal, pemandu, dan transaksi dalam satu ekosistem terpusat.

Masalah: Organizer trip masih mengandalkan WhatsApp/spreadsheet untuk kelola peserta, jadwal, dan pembayaran. Calon peserta kesulitan menemukan dan membandingkan open trip dari berbagai penyelenggara secara transparan. Tidak ada sistem terpusat untuk verifikasi pembayaran, tracking kapasitas slot, dan manajemen guide.

Solusi: Platform berbasis web (Next.js) dengan fitur booking online, manajemen trip, sistem kupon alumni, dashboard bisnis, verifikasi pembayaran manual, dan role-based access control (5 level). Tech stack: Next.js 16, React 19, PostgreSQL, Prisma, NextAuth, MapLibre GL.

Model Bisnis: Multi-tenant SaaS (subscription per organizer), komisi transaksi per booking, add-on margin, kupon alumni untuk retensi.

Target Pasar: Penyelenggara open trip gunung & laut di Indonesia (komunitas hiking, diving, camping). Peserta usia 18-35 tahun. Indonesia memiliki ratusan organizer open trip yang masih beroperasi secara manual."""


async def test():
    search = WebSearchClient()
    llm = UnifiedLLMClient(model=DEFAULT_MODEL)

    output_lines = []

    def out(line=""):
        output_lines.append(line)
        print(line)

    out("# RAG Output — Open Trip Booking Platform")
    out()
    out("## Stimulus")
    out(f"> {STIMULUS[:200]}...")
    out()

    # --- Step 1: Generate queries via LLM ---
    class MockCluster:
        def __init__(self, cluster_id, description):
            self.cluster_id = cluster_id
            self.description = description

    class MockSchema:
        def __init__(self):
            self.scenario_name = "Open Trip Booking Platform — Multi-tenant SaaS untuk organizer trip petualangan di Indonesia"
            self.scenario_description = (
                "Platform digital multi-tenant yang menghubungkan penyelenggara trip petualangan "
                "(gunung, laut, alam) dengan calon peserta. Fitur utama: booking online, manajemen "
                "trip & jadwal, sistem kupon alumni, verifikasi pembayaran manual, role-based access "
                "control. Tech stack: Next.js, PostgreSQL, Prisma. Target: ratusan organizer open trip "
                "di Indonesia yang masih pakai WhatsApp/spreadsheet."
            )
            self.linguistic_clusters = [
                MockCluster("trip_organizer", "Penyelenggara open trip gunung/laut di Indonesia yang saat ini pakai WhatsApp & spreadsheet, evaluasi apakah platform ini worth it"),
                MockCluster("tech_investor", "Angel investor/VC lokal yang menilai kelayakan teknis dan potensi pasar platform travel vertikal di Indonesia"),
                MockCluster("adventure_traveler", "Peserta open trip usia 20-35 tahun yang aktif hiking/diving dan sering cari trip via Instagram/WhatsApp grup"),
                MockCluster("saas_competitor", "Founder platform booking/travel SaaS yang sudah ada di pasar, menilai diferensiasi dan ancaman kompetitif"),
            ]

    schema = MockSchema()

    out("## Step 1: LLM Query Generation")
    out()
    out("Using `generate_perspective_queries()` — LLM generates 2 queries per cluster:")
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
            await asyncio.sleep(1.5)  # Brave API can handle faster than SearXNG

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
    out("The following text block is the `swarm_rag_perspectives` variable injected")
    out("verbatim into the persona-generation prompt that shapes each agent's worldview:")
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

    await search.close()

    # Write to markdown
    outpath = "/mnt/g/WSL/projects/SimulateAI/graphify-out/rag_output_open_trip.md"
    with open(outpath, "w") as f:
        f.write("\n".join(output_lines))
    print(f"\n\n--- Written to {outpath} ---")


if __name__ == "__main__":
    asyncio.run(test())
