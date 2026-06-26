from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float

    @classmethod
    def from_tavily(cls, raw: dict) -> "SearchResult":
        return cls(
            title=str(raw.get("title", "")),
            url=str(raw.get("url", "")),
            content=str(raw.get("content", "")),
            score=float(raw.get("score", 0.0)),
        )


@dataclass
class Citation:
    url: str
    title: str


@dataclass
class ProcessedFacts:
    facts: list[str]
    citations: list[Citation]
    raw_results: list[SearchResult]


@dataclass
class RAGMetadata:
    injections: list[dict] = field(default_factory=list)

    def record(self, point: str, queries: list[str], processed: ProcessedFacts) -> None:
        self.injections.append({
            "point": point,
            "queries": queries,
            "facts": processed.facts,
            "citations": [{"url": c.url, "title": c.title} for c in processed.citations],
        })

    def to_dict(self) -> dict[str, Any]:
        return {"injections": self.injections}
