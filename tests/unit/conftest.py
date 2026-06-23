from src.schema.simulation_schema import (
    ActionDefinition,
    LinguisticCluster,
    ResourceModel,
    SimulationSchema,
)


def make_schema(
    actions: list[tuple[str, bool]] | None = None,
    state_vocabulary: list[str] | None = None,
    clusters: list[str] | None = None,
) -> SimulationSchema:
    action_defs = [
        ActionDefinition(name=name, description=name.lower(), is_terminal=terminal)
        for name, terminal in (actions or [("ADOPT", False), ("AMEND", False), ("REJECT", True)])
    ]
    cluster_defs = [
        LinguisticCluster(cluster_id=c, description="", style_prompt="")
        for c in (clusters or ["a", "b", "c"])
    ]
    return SimulationSchema(
        scenario_name="test",
        scenario_description="test",
        verdict_label="Test Verdict",
        actions=action_defs,
        state_vocabulary=state_vocabulary or ["Neutral", "Skeptical", "Excited", "Cautious", "Resolute"],
        resource_model=ResourceModel(kind="none", resources=[]),
        linguistic_clusters=cluster_defs,
        macro_context=[],
        crisis_dimensions=["x"],
    )
