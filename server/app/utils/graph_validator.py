from __future__ import annotations

from app.core.exceptions import AionError
from app.schemas.planner import GraphEdge, GraphNode


class PlannerValidationException(AionError):
    status_code = 422
    error_code = "PLANNER_VALIDATION_ERROR"


def validate_execution_graph(nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
    node_ids = [node.id for node in nodes]
    unique_ids = set(node_ids)
    if len(node_ids) != len(unique_ids):
        raise PlannerValidationException("Execution graph contains duplicate nodes.")
    if not nodes:
        raise PlannerValidationException("Execution graph must contain at least one node.")

    for edge in edges:
        if edge.source not in unique_ids or edge.target not in unique_ids:
            raise PlannerValidationException("Execution graph contains an edge with an unknown node.")

    incoming = {node_id: 0 for node_id in unique_ids}
    adjacency = {node_id: [] for node_id in unique_ids}
    for edge in edges:
        incoming[edge.target] += 1
        adjacency[edge.source].append(edge.target)

    ready = [node_id for node_id, count in incoming.items() if count == 0]
    visited: list[str] = []
    while ready:
        current = ready.pop()
        visited.append(current)
        for target in adjacency[current]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)

    if len(visited) != len(unique_ids):
        raise PlannerValidationException("Execution graph contains a circular dependency.")

    connected = {edge.source for edge in edges} | {edge.target for edge in edges}
    if len(nodes) > 1:
        orphans = unique_ids - connected
        if orphans:
            raise PlannerValidationException(f"Execution graph contains orphan nodes: {sorted(orphans)}")
