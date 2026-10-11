from collections import defaultdict
from dataclasses import dataclass

from app.parser.models import ParsedFile

TYPE_KINDS = {"class", "interface", "enum", "record"}

RESOLVED = "resolved"
AMBIGUOUS = "ambiguous"    # several candidates (e.g. overloads); never guessed
UNRESOLVED = "unresolved"  # cannot be proven from source alone
EXTERNAL = "external"      # explicitly imported from outside the repository
MAX_AMBIGUOUS = 10


@dataclass(frozen=True)
class Edge:
    source: str            # qualified name of the dependent (A in A -> B)
    target: str | None     # qualified name of the dependency; None if unknown
    kind: str              # extends | implements | calls | instantiates
    status: str
    line: int
    name: str              # text as written in the source


class SymbolIndex:
    def __init__(self, files: list[ParsedFile]) -> None:
        self.symbols = {}
        self.methods: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for f in files:
            for s in f.symbols:
                self.symbols[s.qualified_name] = s
                if s.kind == "method" and s.parent:
                    self.methods[s.parent][s.name].append(s.qualified_name)

    def is_type(self, qn: str) -> bool:
        s = self.symbols.get(qn)
        return s is not None and s.kind in TYPE_KINDS


class Resolver:
    def __init__(self, files: list[ParsedFile]) -> None:
        self.files = files
        self.index = SymbolIndex(files)
        self._supers: dict[str, list[str]] = defaultdict(list)

    def resolve(self) -> list[Edge]:
        edges: list[Edge] = []
        seen: set[Edge] = set()

        def add(source, status, targets, kind, line, name):
            for t in targets or [None]:
                e = Edge(source, t, kind, status, line, name)
                if e not in seen:
                    seen.add(e)
                    edges.append(e)

        # Pass 1: inheritance. Must finish first: method lookup walks supertypes.
        for f in self.files:
            for rel in f.relations:
                status, targets = self._resolve_type(rel.target, f, rel.source)
                if status == RESOLVED:
                    self._supers[rel.source].append(targets[0])
                add(rel.source, status, targets, rel.kind, rel.line, rel.target)

        # Pass 2: calls and instantiations.
        for f in self.files:
            for ref in f.references:
                if ref.caller is None:
                    continue
                if ref.kind == "instantiation":
                    status, targets = self._resolve_type(ref.name, f, ref.caller)
                    add(ref.caller, status, targets, "instantiates", ref.line, ref.name)
                else:
                    status, targets = self._resolve_call(ref, f)
                    add(ref.caller, status, targets, "calls", ref.line, ref.name)
        return edges

    # ---- types ----------------------------------------------------------

    def _type_chain(self, context: str | None) -> list[str]:
        """Enclosing types, innermost first."""
        chain, cur, seen = [], context, set()
        while cur and cur not in seen:
            seen.add(cur)
            sym = self.index.symbols.get(cur)
            if sym is None:
                break
            if sym.kind in TYPE_KINDS:
                chain.append(cur)
            cur = sym.parent
        return chain

    def _resolve_type(self, name: str, f: ParsedFile, context: str | None):
        idx = self.index
        if idx.is_type(name):
            return RESOLVED, [name]
        head, _, rest = name.partition(".")
        base = None

        for outer in self._type_chain(context):          # 1. nested / enclosing
            if idx.symbols[outer].name == head:
                base = outer
                break
            if idx.is_type(f"{outer}.{head}"):
                base = f"{outer}.{head}"
                break

        if base is None:                                  # 2. explicit import
            for imp in f.imports:
                if imp.is_static or imp.is_wildcard:
                    continue
                if imp.name.rsplit(".", 1)[-1] == head:
                    if idx.is_type(imp.name):
                        base = imp.name
                        break
                    return EXTERNAL, []

        if base is None:                                  # 3. same package
            cand = f"{f.package}.{head}" if f.package else head
            if idx.is_type(cand):
                base = cand

        if base is None:                                  # 4. wildcard imports
            cands = []
            for imp in f.imports:
                if imp.is_wildcard and not imp.is_static:
                    c = f"{imp.name}.{head}"
                    if idx.is_type(c) and c not in cands:
                        cands.append(c)
            if len(cands) == 1:
                base = cands[0]
            elif len(cands) > 1:
                return AMBIGUOUS, cands[:MAX_AMBIGUOUS]

        if base is None:
            return UNRESOLVED, []
        if rest:
            full = f"{base}.{rest}"
            return (RESOLVED, [full]) if idx.is_type(full) else (UNRESOLVED, [])
        return RESOLVED, [base]

    # ---- calls ----------------------------------------------------------

    def _find_methods(self, type_qn: str, name: str) -> list[str]:
        """Nearest declaring type wins (BFS up the supertypes)."""
        seen, queue = set(), [type_qn]
        while queue:
            t = queue.pop(0)
            if t in seen:
                continue
            seen.add(t)
            found = self.index.methods.get(t, {}).get(name)
            if found:
                return list(found)
            queue.extend(self._supers.get(t, []))
        return []

    @staticmethod
    def _classify(found: list[str]):
        if not found:
            return UNRESOLVED, []
        if len(found) == 1:
            return RESOLVED, found
        return AMBIGUOUS, found[:MAX_AMBIGUOUS]

    def _resolve_call(self, ref, f: ParsedFile):
        chain = self._type_chain(ref.caller)
        recv = ref.receiver

        if recv is None:
            for t in chain:
                found = self._find_methods(t, ref.name)
                if found:
                    return self._classify(found)
            return UNRESOLVED, []

        if recv == "this" and chain:
            return self._classify(self._find_methods(chain[0], ref.name))

        if recv == "super" and chain:
            for s in self._supers.get(chain[0], []):
                found = self._find_methods(s, ref.name)
                if found:
                    return self._classify(found)
            return UNRESOLVED, []

        # Only a receiver that looks like a class name (SpringApplication.run).
        if recv[0].isupper() and recv.replace(".", "").isidentifier():
            status, targets = self._resolve_type(recv, f, ref.caller)
            if status == RESOLVED:
                return self._classify(self._find_methods(targets[0], ref.name))
            if status == EXTERNAL:
                return EXTERNAL, []

        return UNRESOLVED, []  # receiver is a variable or expression: type unknown