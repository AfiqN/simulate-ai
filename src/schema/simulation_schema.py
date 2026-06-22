from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ActionDefinition:
    name: str
    description: str
    is_terminal: bool = False
    affects_resource: Optional[str] = None


@dataclass
class ResourceDefinition:
    name: str
    description: str = ""
    initial_default: Optional[float] = None
    max_default: Optional[float] = None


@dataclass
class ResourceModel:
    kind: str
    resources: list[ResourceDefinition] = field(default_factory=list)


@dataclass
class LinguisticCluster:
    cluster_id: str
    description: str
    style_prompt: str


@dataclass
class SimulationSchema:
    scenario_name: str
    scenario_description: str
    verdict_label: str
    actions: list[ActionDefinition]
    state_vocabulary: list[str]
    resource_model: ResourceModel
    linguistic_clusters: list[LinguisticCluster]
    macro_context: list[str]
    crisis_dimensions: list[str]

    def action_names(self) -> list[str]:
        return [a.name for a in self.actions]

    def cluster_ids(self) -> list[str]:
        return [c.cluster_id for c in self.linguistic_clusters]

    def get_cluster(self, cluster_id: str) -> Optional[LinguisticCluster]:
        for c in self.linguistic_clusters:
            if c.cluster_id == cluster_id:
                return c
        return None

    def macro_context_text(self) -> str:
        return "\n".join(f"- {line}" for line in self.macro_context)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationSchema":
        actions = [
            ActionDefinition(
                name=str(a["name"]).upper().strip(),
                description=str(a.get("description", "")),
                is_terminal=bool(a.get("is_terminal", False)),
                affects_resource=(a.get("affects_resource") or None),
            )
            for a in data["actions"]
        ]
        rm_data = data["resource_model"]
        kind = str(rm_data.get("kind", "none")).lower().strip()
        resources = [
            ResourceDefinition(
                name=str(r["name"]),
                description=str(r.get("description", "")),
                initial_default=_optional_float(r.get("initial_default")),
                max_default=_optional_float(r.get("max_default")),
            )
            for r in rm_data.get("resources", [])
        ]
        clusters = [
            LinguisticCluster(
                cluster_id=str(c["cluster_id"]),
                description=str(c.get("description", "")),
                style_prompt=str(c["style_prompt"]),
            )
            for c in data["linguistic_clusters"]
        ]
        return cls(
            scenario_name=str(data["scenario_name"]),
            scenario_description=str(data["scenario_description"]),
            verdict_label=str(data["verdict_label"]),
            actions=actions,
            state_vocabulary=[str(s) for s in data["state_vocabulary"]],
            resource_model=ResourceModel(kind=kind, resources=resources),
            linguistic_clusters=clusters,
            macro_context=[str(m) for m in data["macro_context"]],
            crisis_dimensions=[str(c) for c in data["crisis_dimensions"]],
        )


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
