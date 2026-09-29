from __future__ import annotations

import re

from app.schemas.planner import AgentCapability, ExecutionBlueprint, GraphEdge, GraphNode, GraphNodeData, GraphPosition


def normalize_agent_name(name: str) -> str:
    candidate = re.sub(r"Agent$", "", name.strip(), flags=re.IGNORECASE)
    candidate = re.sub(r"(?<!^)(?=[A-Z])", "_", candidate).replace("-", "_").replace(" ", "_")
    return candidate.lower()


def build_execution_graph(
    blueprint: ExecutionBlueprint,
    available_agents: dict[str, AgentCapability],
) -> ExecutionBlueprint:
    available = {normalize_agent_name(name): capability for name, capability in available_agents.items()}
    nodes = blueprint.nodes or []
    edges = blueprint.edges or []
    selected = _unique_available(blueprint.selected_agents, available)

    if not selected and nodes:
        selected = _unique_available((node.data.agent_name or node.id for node in nodes), available)

    nodes = [node for node in nodes if normalize_agent_name(node.data.agent_name or node.id) in selected]
    if not nodes:
        nodes = [
            GraphNode(
                id=agent_name,
                position=GraphPosition(x=(index % 4) * 260, y=(index // 4) * 160),
                data=GraphNodeData(
                    label=_label(agent_name),
                    agent_name=agent_name,
                    priority=available.get(agent_name, AgentCapability(name=agent_name, category="unknown")).priority,
                    parallel=available.get(
                        agent_name, AgentCapability(name=agent_name, category="unknown")
                    ).parallel_capable,
                    status="PENDING",
                ),
            )
            for index, agent_name in enumerate(selected)
        ]
    else:
        nodes = [_normalize_node(node, index, available) for index, node in enumerate(nodes)]

    node_ids = {node.id for node in nodes}
    if edges:
        edges = [
            edge
            for edge in (_normalize_edge(edge) for edge in edges)
            if edge.source in node_ids and edge.target in node_ids
        ]
    if not edges:
        edges = _edges_from_dependencies(nodes, available)

    return blueprint.model_copy(
        update={
            "selected_agents": [node.id for node in nodes],
            "execution_order": [node.id for node in nodes],
            "parallel_groups": [[node.id] for node in nodes],
            "nodes": nodes,
            "edges": edges,
        }
    )


def _normalize_edge(edge: GraphEdge) -> GraphEdge:
    source = normalize_agent_name(edge.source)
    target = normalize_agent_name(edge.target)
    return edge.model_copy(
        update={
            "id": edge.id or f"{source}-{target}",
            "source": source,
            "target": target,
        }
    )


def _normalize_node(
    node: GraphNode,
    index: int,
    available_agents: dict[str, AgentCapability],
) -> GraphNode:
    node_id = normalize_agent_name(node.id)
    agent_name = normalize_agent_name(node.data.agent_name or node_id)
    capability = available_agents.get(agent_name)
    data = node.data.model_copy(
        update={
            "label": node.data.label or _label(agent_name),
            "agent_name": agent_name,
            "priority": node.data.priority or (capability.priority if capability else 3),
            "parallel": node.data.parallel if node.data.parallel is not None else True,
            "status": node.data.status or "PENDING",
        }
    )
    return node.model_copy(
        update={
            "id": node_id,
            "position": node.position or GraphPosition(x=(index % 4) * 260, y=(index // 4) * 160),
            "data": data,
        }
    )


def _edges_from_dependencies(
    nodes: list[GraphNode],
    available_agents: dict[str, AgentCapability],
) -> list[GraphEdge]:
    node_ids = {node.id for node in nodes}
    edges: list[GraphEdge] = []
    for node in nodes:
        deps = [normalize_agent_name(dep) for dep in available_agents.get(node.id, AgentCapability(name=node.id, category="unknown")).dependencies]
        for dep in deps:
            if dep in node_ids:
                edges.append(GraphEdge(id=f"{dep}-{node.id}", source=dep, target=node.id))
    recommendation = next((node.id for node in nodes if node.id == "recommendation"), None)
    if recommendation:
        for node in nodes:
            if node.id != recommendation and not any(edge.source == node.id and edge.target == recommendation for edge in edges):
                edges.append(GraphEdge(id=f"{node.id}-{recommendation}", source=node.id, target=recommendation))
    if not edges and len(nodes) > 1:
        edges = [
            GraphEdge(id=f"{source.id}-{target.id}", source=source.id, target=target.id)
            for source, target in zip(nodes, nodes[1:], strict=False)
        ]
    return edges


def _unique_available(agent_names: object, available_agents: dict[str, AgentCapability]) -> list[str]:
    selected: list[str] = []
    for agent_name in agent_names:
        normalized = normalize_agent_name(str(agent_name))
        if normalized in available_agents and normalized not in selected:
            selected.append(normalized)
    return selected


def _label(agent_name: str) -> str:
    return " ".join(part.capitalize() for part in agent_name.split("_")) + " Agent"
