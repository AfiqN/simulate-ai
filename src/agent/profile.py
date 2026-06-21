from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any
from enum import StrEnum


class AgentState(StrEnum):
    NEUTRAL = "Neutral"
    SKEPTICAL = "Skeptical"
    EXCITED = "Excited"
    ANGRY = "Angry"
    SATISFIED = "Satisfied"
    BORED = "Bored"
    AGGRESSIVE = "Aggressive"
    PARANOID = "Paranoid"
    ANALYTICAL = "Analytical"
    INQUISITIVE = "Inquisitive"

    @classmethod
    def from_str(cls, state_str: str) -> "AgentState":
        """Safely convert any raw string into a valid AgentState Enum."""
        if not state_str:
            return cls.NEUTRAL
        cleaned = state_str.strip().lower().title()  # e.g. "skeptical" -> "Skeptical"
        for member in cls:
            if member.value == cleaned:
                return member
        # Fallbacks for common alternative casings or unaligned names
        if cleaned == "Skeptic":
            return cls.SKEPTICAL
        if cleaned in ("Excitement", "Happy", "Joyful"):
            return cls.EXCITED
        if cleaned in ("Anger", "Annoyed", "Irritated"):
            return cls.ANGRY
        if cleaned == "Boredom":
            return cls.BORED
        return cls.NEUTRAL


@dataclass
class AgentAttributes:
    rationality_index: float  # Scale: 0.0 - 1.0 (How logical they are)
    aggressiveness: float     # Scale: 0.0 - 1.0 (How aggressive/assertive)
    risk_tolerance: float     # Scale: 0.0 - 1.0 (How much risk they can take)


@dataclass
class ResourcePool:
    primary_resource_name: str
    current_balance: float
    max_capacity: float


@dataclass
class AgentProfile:
    agent_id: str
    archetype: str
    attributes: AgentAttributes
    resource_pool: ResourcePool
    memory_vectors: List[str] = field(default_factory=list)
    current_internal_state: AgentState = AgentState.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the agent profile to a dictionary."""
        d = asdict(self)
        d["current_internal_state"] = str(self.current_internal_state)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentProfile":
        """Deserialize an agent profile from a dictionary."""
        attributes_data = data["attributes"]
        resources_data = data["resource_pool"]

        attributes = AgentAttributes(
            rationality_index=float(attributes_data["rationality_index"]),
            aggressiveness=float(attributes_data["aggressiveness"]),
            risk_tolerance=float(attributes_data["risk_tolerance"]),
        )

        resource_pool = ResourcePool(
            primary_resource_name=resources_data["primary_resource_name"],
            current_balance=float(resources_data["current_balance"]),
            max_capacity=float(resources_data["max_capacity"]),
        )

        raw_state = data.get("current_internal_state", "Neutral")
        state_enum = AgentState.from_str(raw_state)

        return cls(
            agent_id=data["agent_id"],
            archetype=data["archetype"],
            attributes=attributes,
            resource_pool=resource_pool,
            memory_vectors=list(data.get("memory_vectors", [])),
            current_internal_state=state_enum,
        )
