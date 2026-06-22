from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class AgentAttributes:
    rationality_index: float
    aggressiveness: float
    risk_tolerance: float


@dataclass
class ResourceBalance:
    name: str
    current: float
    maximum: float


@dataclass
class AgentProfile:
    agent_id: str
    archetype: str
    linguistic_cluster_id: str
    attributes: AgentAttributes
    resources: list[ResourceBalance] = field(default_factory=list)
    memory_vectors: list[str] = field(default_factory=list)
    current_internal_state: str = "Neutral"

    def primary_resource(self) -> Optional[ResourceBalance]:
        return self.resources[0] if self.resources else None

    def find_resource(self, name: str) -> Optional[ResourceBalance]:
        for r in self.resources:
            if r.name == name:
                return r
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProfile":
        attrs = data["attributes"]
        attributes = AgentAttributes(
            rationality_index=float(attrs["rationality_index"]),
            aggressiveness=float(attrs["aggressiveness"]),
            risk_tolerance=float(attrs["risk_tolerance"]),
        )
        resources = [
            ResourceBalance(
                name=str(r["name"]),
                current=float(r["current"]),
                maximum=float(r["maximum"]),
            )
            for r in data.get("resources", [])
        ]
        return cls(
            agent_id=data["agent_id"],
            archetype=data["archetype"],
            linguistic_cluster_id=data["linguistic_cluster_id"],
            attributes=attributes,
            resources=resources,
            memory_vectors=list(data.get("memory_vectors", [])),
            current_internal_state=str(data.get("current_internal_state", "Neutral")),
        )
