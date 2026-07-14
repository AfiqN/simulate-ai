"""Data models for the validation/hindsight testing framework."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ValidationCase:
    """A single historical validation case loaded from YAML."""
    id: str
    name: str
    domain: str
    stimulus: str
    ground_truth: dict[str, Any]
    # Optional metadata
    date: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], filename: str = "") -> "ValidationCase":
        # Derive id from 'id' field, or filename stem, or slugified name
        case_id = data.get("id", "")
        if not case_id and filename:
            case_id = filename.removesuffix(".yaml").removesuffix(".yml")
        if not case_id:
            case_id = data["name"].lower().replace(" ", "_")[:40]
        return cls(
            id=case_id,
            name=data["name"],
            domain=data.get("domain", "general"),
            stimulus=data["stimulus"],
            ground_truth=data["ground_truth"],
            date=data.get("date", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""
    name: str
    score: float  # 0-10
    weight: float
    reasoning: str = ""

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ScoringResult:
    """Scoring result for a single simulation run of a single case."""
    case_id: str
    run_index: int
    verdict_match: DimensionScore
    behavioral_fidelity: DimensionScore
    risk_identification: DimensionScore
    resilience_accuracy: DimensionScore
    raw_llm_response: str = ""
    error: Optional[str] = None

    @property
    def composite_score(self) -> float:
        """Weighted composite score (0-10)."""
        if self.error:
            return 0.0
        return (
            self.verdict_match.weighted_score
            + self.behavioral_fidelity.weighted_score
            + self.risk_identification.weighted_score
            + self.resilience_accuracy.weighted_score
        )

    @property
    def dimensions(self) -> list[DimensionScore]:
        return [
            self.verdict_match,
            self.behavioral_fidelity,
            self.risk_identification,
            self.resilience_accuracy,
        ]


@dataclass
class CaseResult:
    """Aggregated result for a case across multiple runs."""
    case_id: str
    case_name: str
    domain: str
    runs: list[ScoringResult] = field(default_factory=list)
    simulation_error: Optional[str] = None

    @property
    def median_score(self) -> float:
        """Median composite score across runs."""
        scores = sorted(r.composite_score for r in self.runs if not r.error)
        if not scores:
            return 0.0
        mid = len(scores) // 2
        if len(scores) % 2 == 0:
            return (scores[mid - 1] + scores[mid]) / 2
        return scores[mid]

    @property
    def median_dimensions(self) -> dict[str, float]:
        """Median per-dimension scores."""
        dim_names = ["verdict_match", "behavioral_fidelity", "risk_identification", "resilience_accuracy"]
        result = {}
        for dim_name in dim_names:
            scores = sorted(
                getattr(r, dim_name).score for r in self.runs if not r.error
            )
            if not scores:
                result[dim_name] = 0.0
                continue
            mid = len(scores) // 2
            if len(scores) % 2 == 0:
                result[dim_name] = (scores[mid - 1] + scores[mid]) / 2
            else:
                result[dim_name] = scores[mid]
        return result


@dataclass
class ValidationReport:
    """Aggregate report across all validation cases."""
    cases: list[CaseResult] = field(default_factory=list)
    model_used: str = ""
    runs_per_case: int = 3
    timestamp: str = ""

    @property
    def overall_score(self) -> float:
        """Mean of median scores across cases."""
        scores = [c.median_score for c in self.cases if c.runs]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    @property
    def grade(self) -> str:
        """Grade based on overall score thresholds."""
        score = self.overall_score
        if score >= 7.5:
            return "Strong"
        elif score >= 5.5:
            return "Moderate"
        elif score >= 3.5:
            return "Weak"
        else:
            return "Fail"

    @property
    def per_domain(self) -> dict[str, float]:
        """Average median scores grouped by domain."""
        domain_scores: dict[str, list[float]] = {}
        for case in self.cases:
            if case.runs:
                domain_scores.setdefault(case.domain, []).append(case.median_score)
        return {
            domain: sum(scores) / len(scores)
            for domain, scores in domain_scores.items()
        }
