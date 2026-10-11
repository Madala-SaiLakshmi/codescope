from dataclasses import dataclass, field

from app.engine.impact import AffectedSymbol, ChangedSymbol, ImpactResult

TEST_SUFFIXES = ("Test", "Tests", "IT", "TestCase")


def is_test_path(path: str | None) -> bool:
    p = (path or "").replace("\\", "/")
    return "/src/test/" in f"/{p}" or p.startswith("test/") or "/test/" in p


def is_test_class_name(name: str) -> bool:
    return name.endswith(TEST_SUFFIXES) or name.startswith("Test")


def top_class(qualified_name: str) -> str:
    """'a.b.Owner.save(int)' -> 'a.b.Owner'; nested classes roll up into the outermost class."""
    base = qualified_name.split("(")[0]
    parts = base.split(".")
    for i, part in enumerate(parts):
        if part[:1].isupper():
            return ".".join(parts[: i + 1])
    return base


def simple_name(qualified_name: str) -> str:
    return top_class(qualified_name).split(".")[-1]


def package_of(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


@dataclass
class TestCandidate:
    path: str
    test_class: str
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


def select_tests(result: ImpactResult, test_files: dict[str, list[str]]) -> list[TestCandidate]:
    """test_files maps a test file path to the qualified names of types declared in it."""
    candidates: dict[str, TestCandidate] = {}

    def cand(path: str, cls: str) -> TestCandidate:
        if path not in candidates:
            candidates[path] = TestCandidate(path, cls)
        return candidates[path]

    changed_names = {simple_name(c.qualified_name): c for c in result.changed}
    changed_dirs = {package_of(c.path) for c in result.changed if c.path and not is_test_path(c.path)}

    # 1. Graph evidence: affected symbols that live in test code.
    best: dict[str, AffectedSymbol] = {}
    for a in result.affected:
        if is_test_path(a.path) or is_test_class_name(simple_name(a.qualified_name)):
            prev = best.get(top_class(a.qualified_name))
            if prev is None or (a.distance, not a.certain) < (prev.distance, not prev.certain):
                best[top_class(a.qualified_name)] = a
    path_of = {}
    for path, types in test_files.items():
        for t in types:
            path_of[t] = path
    for cls, a in best.items():
        path = a.path or path_of.get(cls)
        if not path:
            continue
        c = cand(path, cls)
        points = max(10.0, 60.0 - 15.0 * (a.distance - 1)) * (1.0 if a.certain else 0.6)
        c.score += points
        kind = "confirmed" if a.certain else "uncertain"
        c.reasons.append(
            f"{a.qualified_name.split('.')[-1]} reaches changed code {a.distance} step(s) away "
            f"via a {kind} path: " + " -> ".join(p.split('.')[-1] for p in a.via)
        )

    # 2. Naming convention: OwnerTests / OwnerTest / TestOwner for a changed Owner.
    for path, types in test_files.items():
        for t in types:
            name = t.split(".")[-1]
            core = name
            for suf in TEST_SUFFIXES:
                if core.endswith(suf):
                    core = core[: -len(suf)]
                    break
            else:
                core = core[4:] if core.startswith("Test") else core
            if core and core in changed_names:
                c = cand(path, t)
                c.score += 30.0
                c.reasons.append(f"name matches changed class {core}")

    # 3. Same package as changed production code.
    for path in test_files:
        mirrored = package_of(path).replace("src/test/java", "src/main/java")
        if mirrored in changed_dirs:
            c = cand(path, next(iter(test_files[path]), path))
            c.score += 10.0
            c.reasons.append("in the same package as changed code")

    out = list(candidates.values())
    for c in out:
        c.score = min(100.0, round(c.score, 1))
    return sorted(out, key=lambda c: (-c.score, c.path))


@dataclass(frozen=True)
class RiskFactor:
    name: str
    points: float
    max_points: float
    detail: str


@dataclass
class RiskScore:
    total: float
    level: str
    factors: list[RiskFactor]


def _scaled(value: float, full_at: float, max_points: float) -> float:
    return round(min(value / full_at, 1.0) * max_points, 1)


def compute_risk(
    result: ImpactResult,
    selected_tests: list[TestCandidate],
    total_symbols: int,
    centrality: dict[str, int] | None = None,
) -> RiskScore:
    """Rule-based score, 0-100. Weights are documented starting points, not fitted to data.

    size 20 | blast radius 30 | depth 15 | centrality 15 | test gap 10 | uncertainty 10
    """
    changed = [c for c in result.changed if not is_test_path(c.path)]
    affected = [a for a in result.affected if not is_test_path(a.path)]
    n_changed, n_affected = len(changed), len(affected)
    depth = max((a.distance for a in affected), default=0)
    top = max((centrality or {}).get(c.qualified_name, 0) for c in changed) if changed else 0
    covered = {a.root for a in result.affected if is_test_path(a.path)}
    unlinked = [c for c in changed if c.change != "added" and c.qualified_name not in covered]
    gap = len(unlinked) / n_changed if n_changed else 0.0
    uncertain_share = (
        sum(1 for a in affected if not a.certain) / n_affected if n_affected else 0.0
    )
    unmapped = len(result.uncertainties)

    factors = [
        RiskFactor("Size of change", _scaled(n_changed, 20, 20),
                   20, f"{n_changed} changed symbol(s) (full points at 20)"),
        RiskFactor("Blast radius", _scaled(n_affected, 30, 30),
                   30, f"{n_affected} potentially affected symbol(s) (full points at 30)"),
        RiskFactor("Dependency depth", _scaled(depth, 4, 15),
                   15, f"affects code up to {depth} step(s) away (full points at 4)"),
        RiskFactor("Centrality", _scaled(top, 15, 15),
                   15, f"most-depended-on changed symbol has {top} direct dependent(s) (full at 15)"),
        RiskFactor("Test gap", round(gap * 10, 1), 10,
                   f"{len(unlinked)} of {n_changed} changed symbol(s) have no test reaching them"),
        RiskFactor("Uncertainty", round(min(uncertain_share + min(unmapped, 10) / 10, 1.0) * 10, 1),
                   10, f"{unmapped} change(s) could not be mapped; "
                       f"{round(uncertain_share * 100)}% of affected paths are uncertain"),
    ]
    total = round(sum(f.points for f in factors), 1)
    level = "low" if total < 25 else "medium" if total < 50 else "high" if total < 75 else "critical"
    return RiskScore(total, level, factors)
