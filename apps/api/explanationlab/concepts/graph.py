"""Concept dependency graph utilities.

The graph itself is inferred by a model and is therefore a **hypothesis**. What
this module does is deterministic and checkable: validate the structure, detect
cycles, derive a teaching order, and compare that order against the order the
explanation actually uses.

That last comparison is the measurable part of H2. "Concepts are introduced out
of dependency order" is a concrete, reproducible observation about a text, in a
way that "the explanation is poorly sequenced" is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PREREQUISITE_RELATIONS = {"prerequisite_for", "motivates"}


class GraphValidationError(ValueError):
    pass


@dataclass(slots=True)
class ValidatedGraph:
    nodes: list[dict]
    edges: list[dict]
    teaching_order: list[str] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    dropped_edges: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "teaching_order": self.teaching_order,
            "cycles": self.cycles,
            "dropped_edges": self.dropped_edges,
            "warnings": self.warnings,
            "is_hypothesis": True,
        }


def validate(raw: dict) -> ValidatedGraph:
    """Normalise and validate a model-produced graph.

    Models produce edges referencing nodes they never declared, and duplicate
    nodes with different casing. Both are handled here rather than being allowed
    to reach the UI as a broken render.
    """
    nodes_raw = raw.get("nodes") or []
    edges_raw = raw.get("edges") or []
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        raise GraphValidationError("'nodes' and 'edges' must both be lists.")

    nodes: list[dict] = []
    seen: dict[str, str] = {}
    warnings: list[str] = []

    for node in nodes_raw:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or node.get("label") or "").strip()
        if not node_id:
            continue
        key = _slug(node_id)
        if key in seen:
            warnings.append(f"Duplicate concept '{node_id}' merged.")
            continue
        seen[key] = key
        nodes.append(
            {
                "id": key,
                "label": str(node.get("label") or node_id),
                "importance": node.get("importance") or "core",
                "introduced_in_text": bool(node.get("introduced_in_text", True)),
                "explained_in_text": bool(node.get("explained_in_text", True)),
            }
        )

    edges: list[dict] = []
    dropped: list[dict] = []
    for edge in edges_raw:
        if not isinstance(edge, dict):
            continue
        src = _slug(str(edge.get("source") or ""))
        dst = _slug(str(edge.get("target") or ""))
        if not src or not dst:
            dropped.append({**edge, "reason": "missing source or target"})
            continue
        if src == dst:
            dropped.append({**edge, "reason": "self-loop"})
            continue
        if src not in seen or dst not in seen:
            dropped.append({**edge, "reason": "references an undeclared concept"})
            continue
        edges.append(
            {
                "source": src,
                "target": dst,
                "relation": edge.get("relation") or "prerequisite_for",
                "confidence": edge.get("confidence") or "medium",
            }
        )

    if dropped:
        warnings.append(f"{len(dropped)} edge(s) dropped as unusable.")

    graph = ValidatedGraph(nodes=nodes, edges=edges, dropped_edges=dropped, warnings=warnings)
    graph.cycles = find_cycles(nodes, edges)
    if graph.cycles:
        graph.warnings.append(
            f"{len(graph.cycles)} dependency cycle(s) detected. A cycle means the inferred "
            "prerequisites are mutually dependent, so no strict teaching order exists; the "
            "order below breaks cycles arbitrarily."
        )
    graph.teaching_order = topological_order(nodes, edges)
    return graph


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def find_cycles(nodes: list[dict], edges: list[dict]) -> list[list[str]]:
    """Return elementary cycles over prerequisite-style edges (DFS, iterative)."""
    adjacency: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in edges:
        if e.get("relation") in PREREQUISITE_RELATIONS:
            adjacency[e["source"]].append(e["target"])

    cycles: list[list[str]] = []
    seen_signatures: set[frozenset[str]] = set()
    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(adjacency, WHITE)

    for root in adjacency:
        if colour[root] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(root, 0)]
        path: list[str] = []
        colour[root] = GREY
        path.append(root)
        while stack:
            node, index = stack[-1]
            neighbours = adjacency[node]
            if index < len(neighbours):
                stack[-1] = (node, index + 1)
                nxt = neighbours[index]
                if colour.get(nxt) == GREY:
                    start = path.index(nxt)
                    cycle = path[start:] + [nxt]
                    signature = frozenset(cycle)
                    if signature not in seen_signatures:
                        seen_signatures.add(signature)
                        cycles.append(cycle)
                elif colour.get(nxt) == WHITE:
                    colour[nxt] = GREY
                    path.append(nxt)
                    stack.append((nxt, 0))
            else:
                colour[node] = BLACK
                stack.pop()
                if path:
                    path.pop()
    return cycles


def topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Kahn's algorithm; remaining nodes appended when cycles block progress.

    Ties are broken by declaration order so the output is stable for a given
    graph — reproducibility matters more here than finding a "nicest" order.
    """
    order_index = {n["id"]: i for i, n in enumerate(nodes)}
    indegree = dict.fromkeys(order_index, 0)
    adjacency: dict[str, list[str]] = {nid: [] for nid in order_index}

    for e in edges:
        if e.get("relation") not in PREREQUISITE_RELATIONS:
            continue
        adjacency[e["source"]].append(e["target"])
        indegree[e["target"]] += 1

    ready = sorted([n for n, d in indegree.items() if d == 0], key=lambda n: order_index[n])
    result: list[str] = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        for nxt in adjacency[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort(key=lambda n: order_index[n])

    if len(result) < len(order_index):
        remaining = [n for n in order_index if n not in result]
        remaining.sort(key=lambda n: order_index[n])
        result.extend(remaining)
    return result


def first_mention_order(text: str, nodes: list[dict]) -> list[str]:
    """Order concepts by where their label first appears in the text."""
    lowered = text.lower()
    positions: list[tuple[int, str]] = []
    for node in nodes:
        label = str(node.get("label") or node["id"]).lower()
        pos = lowered.find(label)
        if pos == -1:
            # Try the slug's words, for labels the text phrases differently.
            words = [w for w in node["id"].split("_") if len(w) > 3]
            pos = min((lowered.find(w) for w in words if lowered.find(w) != -1), default=-1)
        if pos != -1:
            positions.append((pos, node["id"]))
    positions.sort()
    return [nid for _, nid in positions]


def sequencing_violations(text: str, graph: ValidatedGraph) -> dict:
    """Count prerequisites introduced *after* the concepts that depend on them.

    This is the concrete, model-free measure behind "terminology introduction
    order" in §8.1 of the brief.
    """
    mention = first_mention_order(text, graph.nodes)
    rank = {nid: i for i, nid in enumerate(mention)}

    violations: list[dict] = []
    checked = 0
    for edge in graph.edges:
        if edge.get("relation") not in PREREQUISITE_RELATIONS:
            continue
        src, dst = edge["source"], edge["target"]
        if src not in rank or dst not in rank:
            continue
        checked += 1
        if rank[src] > rank[dst]:
            violations.append(
                {
                    "prerequisite": src,
                    "dependent": dst,
                    "relation": edge["relation"],
                    "detail": (
                        f"'{src}' is used as a prerequisite for '{dst}' but is first "
                        "mentioned later in the text."
                    ),
                }
            )

    unmentioned = [n["id"] for n in graph.nodes if n["id"] not in rank]
    return {
        "edges_checked": checked,
        "violation_count": len(violations),
        "violations": violations,
        "violation_rate": round(len(violations) / checked, 4) if checked else None,
        "concepts_not_located_in_text": unmentioned,
        "mention_order": mention,
        "teaching_order": graph.teaching_order,
        "note": (
            "Prerequisite edges are model-inferred hypotheses. This measures the text "
            "against that hypothesis, not against ground truth."
        ),
    }
