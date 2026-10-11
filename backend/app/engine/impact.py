from collections import defaultdict, deque
from dataclasses import dataclass, field

from app.engine.changes import FileChange
from app.engine.graph import DependencyGraph
from app.parser.models import ParsedFile, SymbolInfo

MAX_RANGE_LINES = 20000


@dataclass(frozen=True)
class ChangedSymbol:
    qualified_name: str
    kind: str
    path: str
    change: str            # modified | added | removed


@dataclass(frozen=True)
class AffectedSymbol:
    qualified_name: str
    kind: str
    path: str | None
    distance: int
    certain: bool          # True if some path uses only confirmed (resolved) edges
    root: str              # the changed symbol this was reached from
    via: tuple[str, ...]   # affected -> ... -> root (each depends on the next)


@dataclass(frozen=True)
class Uncertainty:
    path: str
    message: str


@dataclass
class ImpactResult:
    changes: list[FileChange]
    changed: list[ChangedSymbol] = field(default_factory=list)
    affected: list[AffectedSymbol] = field(default_factory=list)
    uncertainties: list[Uncertainty] = field(default_factory=list)


def _map_ranges(symbols: list[SymbolInfo], ranges):
    """Innermost symbol per changed line. Returns (symbols, unmapped line ranges)."""
    found: dict[str, SymbolInfo] = {}
    unmapped: list[tuple[int, int]] = []
    for start, end in ranges:
        if end - start + 1 > MAX_RANGE_LINES:
            for s in symbols:
                if s.start_line <= end and s.end_line >= start:
                    found[s.qualified_name] = s
            continue
        gap = None
        for line in range(start, end + 1):
            best = None
            for s in symbols:
                if s.start_line <= line <= s.end_line:
                    key = (s.end_line - s.start_line, -len(s.qualified_name))
                    if best is None or key < best[0]:
                        best = (key, s)
            if best is None:
                gap = (gap[0], line) if gap else (line, line)
            else:
                found[best[1].qualified_name] = best[1]
                if gap:
                    unmapped.append(gap)
                    gap = None
        if gap:
            unmapped.append(gap)
    return list(found.values()), unmapped


def _reverse_adjacency(graph: DependencyGraph):
    rev = defaultdict(list)
    for u, v, _kinds, status in graph.edge_list():
        rev[v].append((u, status))
    for v in rev:
        rev[v].sort()
    return rev


def _bfs(rev, roots: list[str], strict: bool, max_depth: int | None):
    parent = {r: None for r in roots}
    dist = {r: 0 for r in roots}
    root_of = {r: r for r in roots}
    queue = deque(roots)
    while queue:
        v = queue.popleft()
        if max_depth is not None and dist[v] >= max_depth:
            continue
        for u, status in rev.get(v, []):
            if strict and status != "resolved":
                continue
            if u in parent:
                continue
            parent[u] = v
            dist[u] = dist[v] + 1
            root_of[u] = root_of[v]
            queue.append(u)
    return parent, dist, root_of


def _affected_from(graph: DependencyGraph, roots, max_depth) -> dict[str, AffectedSymbol]:
    nodes = set(graph.nodes())
    roots = sorted(r for r in roots if r in nodes)
    if not roots:
        return {}
    rev = _reverse_adjacency(graph)
    loose = _bfs(rev, roots, False, max_depth)
    strict = _bfs(rev, roots, True, max_depth)
    root_set = set(roots)
    out: dict[str, AffectedSymbol] = {}
    for node in loose[0]:
        if node in root_set:
            continue
        (parent, dist, root_of), certain = (strict, True) if node in strict[0] else (loose, False)
        path, cur = [], node
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        data = graph.node_data(node)
        out[node] = AffectedSymbol(
            node, data["kind"], data.get("path"), dist[node], certain, root_of[node], tuple(path)
        )
    return out


def compute_impact(
    changes: list[FileChange],
    target_files: list[ParsedFile],
    target_graph: DependencyGraph,
    base_files: list[ParsedFile] | None = None,
    base_graph: DependencyGraph | None = None,
    max_depth: int | None = None,
) -> ImpactResult:
    result = ImpactResult(changes=changes)
    t_by_path = {f.path: f for f in target_files}
    b_by_path = {f.path: f for f in (base_files or [])}
    target_nodes = set(target_graph.nodes())
    changed: dict[str, ChangedSymbol] = {}
    removed: dict[str, ChangedSymbol] = {}

    def note(path: str, message: str) -> None:
        result.uncertainties.append(Uncertainty(path, message))

    for ch in changes:
        if not ch.path.endswith(".java"):
            continue

        if ch.change_type == "deleted":
            if base_files is None:
                note(ch.path, "File deleted, but no base analysis was provided; its dependents cannot be found")
                continue
            bf = b_by_path.get(ch.path)
            if bf is None:
                note(ch.path, "Deleted file was not analyzed in the base revision")
                continue
            for s in bf.symbols:
                removed[s.qualified_name] = ChangedSymbol(s.qualified_name, s.kind, bf.path, "removed")
            continue

        tf = t_by_path.get(ch.path)
        if tf is None:
            note(ch.path, "File was not analyzed in the target revision (skipped or too large)")
            continue
        if tf.has_syntax_errors:
            note(ch.path, "File has syntax errors; symbol mapping may be incomplete")

        if ch.change_type == "added":
            for s in tf.symbols:
                changed[s.qualified_name] = ChangedSymbol(s.qualified_name, s.kind, tf.path, "added")
            continue

        if not ch.new_ranges and not ch.old_ranges:
            continue  # pure rename or mode change: no code changed

        syms, unmapped = _map_ranges(tf.symbols, ch.new_ranges)
        for s in syms:
            changed[s.qualified_name] = ChangedSymbol(s.qualified_name, s.kind, tf.path, "modified")
        for a, b in unmapped:
            note(ch.path, f"Changed lines {a}-{b} are outside any class or method "
                          "(imports, package or comments); impact cannot be traced")

        if ch.old_ranges:
            if base_files is None:
                note(ch.path, "Removed code cannot be checked: no base analysis was provided")
                continue
            bf = b_by_path.get(ch.old_path or ch.path)
            if bf is None:
                note(ch.path, "Base version of this file was not analyzed")
                continue
            old_syms, _ = _map_ranges(bf.symbols, ch.old_ranges)
            for s in old_syms:
                if s.qualified_name not in target_nodes:
                    removed[s.qualified_name] = ChangedSymbol(s.qualified_name, s.kind, bf.path, "removed")

    affected = _affected_from(target_graph, list(changed), max_depth)
    if base_graph is not None and removed:
        for name, item in _affected_from(base_graph, list(removed), max_depth).items():
            if name in target_nodes and name not in changed and name not in affected:
                affected[name] = item

    result.changed = sorted(list(changed.values()) + list(removed.values()),
                            key=lambda c: (c.change, c.qualified_name))
    result.affected = sorted(affected.values(), key=lambda a: (a.distance, a.qualified_name))
    return result
