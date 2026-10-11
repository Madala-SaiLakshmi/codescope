import networkx as nx

from app.engine.resolver import AMBIGUOUS, RESOLVED, TYPE_KINDS, Edge
from app.parser.models import ParsedFile


class DependencyGraph:
    def __init__(self) -> None:
        self._g = nx.DiGraph()

    @classmethod
    def build(cls, files: list[ParsedFile], edges: list[Edge]) -> "DependencyGraph":
        graph = cls()
        for f in files:
            for s in f.symbols:
                graph._g.add_node(
                    s.qualified_name, kind=s.kind, name=s.name, parent=s.parent,
                    path=f.path, start_line=s.start_line, end_line=s.end_line,
                )
        for e in edges:
            graph._add_edge(e)
        return graph

    def _add_edge(self, e: Edge) -> None:
        if e.target is None or e.status not in (RESOLVED, AMBIGUOUS):
            return
        if e.source == e.target or e.source not in self._g or e.target not in self._g:
            return  # recursion is not a circular dependency
        if self._g.has_edge(e.source, e.target):
            attrs = self._g[e.source][e.target]
            attrs["kinds"].add(e.kind)
            if e.status == RESOLVED:
                attrs["status"] = RESOLVED
        else:
            self._g.add_edge(e.source, e.target, kinds={e.kind}, status=e.status)

    # ---- queries --------------------------------------------------------

    def _view(self, include_uncertain: bool):
        if include_uncertain:
            return self._g
        return nx.subgraph_view(
            self._g, filter_edge=lambda u, v: self._g[u][v]["status"] == RESOLVED
        )

    def _require(self, node: str) -> None:
        if node not in self._g:
            raise KeyError(node)

    def nodes(self) -> list[str]:
        return list(self._g.nodes)

    def node_count(self) -> int:
        return self._g.number_of_nodes()

    def edge_count(self) -> int:
        return self._g.number_of_edges()

    def dependencies(self, node: str, include_uncertain: bool = True) -> set[str]:
        self._require(node)
        return set(self._view(include_uncertain).successors(node))

    def dependents(self, node: str, include_uncertain: bool = True) -> set[str]:
        self._require(node)
        return set(self._view(include_uncertain).predecessors(node))

    def transitive_dependencies(self, node: str, include_uncertain: bool = True) -> set[str]:
        self._require(node)
        return nx.descendants(self._view(include_uncertain), node)

    def transitive_dependents(self, node: str, include_uncertain: bool = True) -> set[str]:
        self._require(node)
        return nx.ancestors(self._view(include_uncertain), node)

    def shortest_path(self, source: str, target: str, include_uncertain: bool = True):
        self._require(source)
        self._require(target)
        try:
            return nx.shortest_path(self._view(include_uncertain), source, target)
        except nx.NetworkXNoPath:
            return None

    def explain_impact(self, affected: str, changed: str, include_uncertain: bool = True):
        """Path affected -> ... -> changed (the affected node depends on the changed one)."""
        return self.shortest_path(affected, changed, include_uncertain)

    def cycles(self, include_uncertain: bool = True) -> list[list[str]]:
        comps = [
            sorted(c)
            for c in nx.strongly_connected_components(self._view(include_uncertain))
            if len(c) > 1
        ]
        return sorted(comps, key=lambda c: (-len(c), c))

    def collapse_to_types(self) -> "DependencyGraph":
        """Merge each method into its enclosing type: the view for circular-dependency reports."""
        out = DependencyGraph()
        for n, a in self._g.nodes(data=True):
            if a["kind"] in TYPE_KINDS:
                out._g.add_node(n, **a)

        def owner(n: str):
            a = self._g.nodes[n]
            return n if a["kind"] in TYPE_KINDS else a["parent"]

        for u, v, a in self._g.edges(data=True):
            ou, ov = owner(u), owner(v)
            if ou is None or ov is None or ou == ov or ou not in out._g or ov not in out._g:
                continue
            if out._g.has_edge(ou, ov):
                out._g[ou][ov]["kinds"] |= a["kinds"]
                if a["status"] == RESOLVED:
                    out._g[ou][ov]["status"] = RESOLVED
            else:
                out._g.add_edge(ou, ov, kinds=set(a["kinds"]), status=a["status"])
        return out