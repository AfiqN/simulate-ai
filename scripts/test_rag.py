"""Quick test to see what RAG produces for a typical simulation."""
import asyncio
from src.rag.client import WebSearchClient


async def demo():
    client = WebSearchClient()

    queries = [
        "open trip platform Indonesia market size 2024",
        "travel tech startup Indonesia payment gateway challenge",
        "Indonesian adventure tourism regulations",
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print(f"{'='*60}")
        results = await client.search(q, max_results=3)
        for r in results:
            print(f"\n  [{r.score:.2f}] {r.title}")
            print(f"  URL: {r.url}")
            print(f"  Content: {r.content[:200]}...")

    await client.close()


if __name__ == "__main__":
    asyncio.run(demo())
