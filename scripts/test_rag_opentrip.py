"""Test RAG with Open Trip Booking Platform stimulus — full output."""
import asyncio
import json
import sys
sys.path.insert(0, "/mnt/g/WSL/projects/SimulateAI")

from src.rag.client import WebSearchClient
from src.rag.processor import extract_facts_with_llm
from src.llm.client import UnifiedLLMClient
from config import DEFAULT_MODEL


STIMULUS = """Open Trip Booking Platform — Proposal Bisnis

---
Ringkasan Eksekutif

Open Trip adalah platform digital multi-tenant yang menghubungkan penyelenggara trip petualangan (gunung, laut, alam) dengan calon peserta. Platform ini memungkinkan banyak organizer mendaftarkan bisnisnya, mengelola trip, jadwal, pemandu, dan transaksi dalam satu ekosistem terpusat.

---
Masalah yang Diselesaikan

1. Organizer trip masih mengandalkan WhatsApp/spreadsheet untuk kelola peserta, jadwal, dan pembayaran — rawan human error dan tidak scalable.
2. Calon peserta kesulitan menemukan dan membandingkan open trip dari berbagai penyelenggara secara transparan.
3. Tidak ada sistem terpusat untuk verifikasi pembayaran, tracking kapasitas slot, dan manajemen guide.

---
Solusi

Platform berbasis web (Next.js) yang menyediakan:

Untuk Peserta (Customer):
- Pencarian & discovery trip berdasarkan destinasi, gunung, atau organizer
- Booking online dengan pilihan paket, add-on, dan meeting point
- Sistem kupon & diskon alumni (peserta yang sudah pernah ikut trip mendapat harga khusus)
- Dashboard riwayat transaksi

Untuk Organizer (Admin & Supervisor):
- Dashboard bisnis dengan statistik real-time
- Manajemen trip lengkap (itinerary dengan peta interaktif, paket harga bertingkat, add-on, foto)
- Manajemen jadwal dengan kapasitas slot otomatis
- Verifikasi pembayaran manual (transfer/cash dengan bukti bayar)
- Sistem DP (Down Payment) dengan persentase yang bisa diatur per trip
- Manajemen guide & supervisor dengan permission granular
- Manajemen kupon (fixed/persentase, global/per-trip, berbasis alumni)

Untuk Guide:
- Portal khusus untuk melihat jadwal yang ditugaskan
- Kelola peserta per jadwal
- Riwayat trip yang telah dilaksanakan

Untuk Superadmin (Platform Owner):
- Overview seluruh organizer di platform
- Statistik global (total organizer, admin, trip, user, booking, guide)
- CRUD organizer dan admin

---
Model Bisnis

- Multi-tenant SaaS: Setiap organizer adalah tenant independen — potensi subscription fee per organizer
- Komisi transaksi: Platform bisa mengambil persentase dari setiap booking yang berhasil
- Add-on & upsell: Organizer menjual perlengkapan tambahan — platform bisa ambil margin
- Kupon alumni: Meningkatkan repeat booking dan retensi pelanggan

Saat ini pembayaran bersifat manual verification (transfer bank / cash + upload bukti bayar).

---
Target Pasar

- Primer: Penyelenggara open trip gunung & laut di Indonesia (komunitas hiking, diving, camping)
- Sekunder: Peserta usia 18-35 tahun yang aktif mencari pengalaman outdoor
- Skala: Indonesia memiliki ratusan organizer open trip yang masih beroperasi secara manual"""


async def test():
    search = WebSearchClient()
    llm = UnifiedLLMClient(model=DEFAULT_MODEL)

    output_lines = []

    def out(line=""):
        output_lines.append(line)
        print(line)

    out("# RAG Output — Open Trip Booking Platform")
    out()
    out("## Stimulus (abbreviated)")
    out(f"> {STIMULUS[:150]}...")
    out()

    # Simulate dual-query approach (sentiment + context per role)
    roles = [
        {
            "cluster_id": "trip_organizer",
            "description": "Open trip organizer/operator managing adventure trips",
            "queries": [
                "open trip Indonesia organizer complaints managing customers",
                "adventure tourism booking platform Indonesia market 2024",
            ],
        },
        {
            "cluster_id": "young_adventurer",
            "description": "Young Indonesian outdoor enthusiast seeking trip experiences",
            "queries": [
                "open trip Indonesia bad experience scam organizer review",
                "Indonesia adventure tourism millennials outdoor activity growth",
            ],
        },
        {
            "cluster_id": "travel_tech_investor",
            "description": "Investor evaluating travel tech / marketplace SaaS in Southeast Asia",
            "queries": [
                "travel tech startup Indonesia challenges investor skepticism",
                "Indonesia travel booking SaaS market opportunity funding 2024",
            ],
        },
    ]

    all_perspectives = {}

    for role in roles:
        cluster_id = role["cluster_id"]
        out(f"---")
        out(f"## Cluster: `{cluster_id}`")
        out(f"**Description:** {role['description']}")
        out()

        queries = role["queries"]
        out(f"### Queries Generated")
        out(f"- **[SENTIMENT]** `{queries[0]}`")
        out(f"- **[CONTEXT]** `{queries[1]}`")
        out()

        cluster_facts = []

        for qi, query in enumerate(queries):
            query_type = "SENTIMENT" if qi == 0 else "CONTEXT"
            # Sentiment queries use social mode (allow X, Reddit, Kaskus)
            is_sentiment = (qi == 0)
            results = await search.search(query, max_results=3, allow_social=is_sentiment)
            # Delay between queries to avoid SearXNG engine rate limits
            await asyncio.sleep(2.0)
            out(f"### Search Results for [{query_type}] query")
            out(f"Raw results returned: {len(results)}")
            out()

            if results:
                for i, r in enumerate(results, 1):
                    out(f"  {i}. **{r.title[:80]}**")
                    out(f"     URL: {r.url[:100]}")
                    content_preview = r.content[:200].replace("\n", " ") if r.content else "(no content)"
                    out(f"     Content preview: {content_preview}...")
                    out()

                # LLM extraction
                facts = await extract_facts_with_llm(
                    llm, results, query,
                    context=f"Scenario: Open Trip Booking Platform. Role: {cluster_id} — {role['description']}",
                    max_facts=4,
                )
                out(f"### Extracted Facts [{query_type}]")
                for i, f in enumerate(facts.facts, 1):
                    out(f"  {i}. {f}")
                    cluster_facts.append(f)
                out()
                out(f"**Citations:**")
                for c in facts.citations:
                    out(f"  - [{c.title[:70]}]({c.url})")
                out()
            else:
                out("  (no results)")
                out()

        all_perspectives[cluster_id] = cluster_facts

    # Now show EXACTLY what gets fed to the Swarm Generator
    out("---")
    out("---")
    out()
    out("# FINAL OUTPUT: What Gets Fed to the LLM (Swarm Generator)")
    out()
    out("The following block is injected into the persona-generation prompt verbatim:")
    out()
    out("```")
    out()
    out("STAKEHOLDER PERSPECTIVES (real-world attitudes — use to shape each agent's worldview):")
    out()
    for cluster_id, facts in all_perspectives.items():
        desc = next(r["description"] for r in roles if r["cluster_id"] == cluster_id)
        if facts:
            out(f'  For cluster "{cluster_id}" ({desc}):')
            for fact in facts:
                out(f"    - {fact}")
            out()
    out("Use these real-world perspectives to shape each agent's memory_vectors and attitudes.")
    out("Agents should reflect the genuine sentiments and worldview of their stakeholder group.")
    out("Do NOT copy verbatim — synthesize into character-defining beliefs.")
    out()
    out("```")
    out()

    # Also show what crisis facts would look like
    out("---")
    out()
    out("# CRISIS INJECTION (Round 3)")
    out()
    out("Separately, a crisis-specific RAG search runs after Round 2 debate.")
    out("It uses the debate transcript to generate a targeted query.")
    out("Example crisis query for this scenario might be:")
    out('  `"open trip accident Indonesia safety incident 2024"`')
    out()
    out("The extracted facts would then appear in the crisis prompt as:")
    out()
    out("```")
    out("REAL-WORLD PRECEDENTS (use to ground the crisis in actual events):")
    out("- [fact 1 from crisis search]")
    out("- [fact 2 from crisis search]")
    out()
    out("Base your crisis event on a real or plausible variation of these precedents.")
    out("```")

    await search.close()

    # Write to markdown
    with open("/mnt/g/WSL/projects/SimulateAI/graphify-out/rag_output_opentrip.md", "w") as f:
        f.write("\n".join(output_lines))


if __name__ == "__main__":
    asyncio.run(test())
