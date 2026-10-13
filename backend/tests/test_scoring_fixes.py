from app.engine.changes import FileChange
from app.engine.graph import DependencyGraph
from app.engine.impact import (
    AffectedSymbol,
    ChangedSymbol,
    ImpactResult,
    direct_dependent_counts,
)
from app.engine.resolver import Resolver
from app.engine.tests_select import select_tests
from app.parser.java_parser import JavaParser

MAIN = "src/main/java/app/Owner.java"
T1 = "src/test/java/app/OwnerTests.java"
T2 = "src/test/java/app/ServiceTests.java"
T3 = "src/test/java/app/PkgOnlyTests.java"


def result():
    return ImpactResult(
        changes=[FileChange(MAIN, "modified")],
        changed=[ChangedSymbol("app.Owner.save()", "method", MAIN, "modified")],
        affected=[
            AffectedSymbol("app.OwnerTests.t()", "method", T1, 1, True, "app.Owner.save()",
                           ("app.OwnerTests.t()", "app.Owner.save()")),
            AffectedSymbol("app.ServiceTests.t()", "method", T2, 3, True, "app.Owner.save()",
                           ("app.ServiceTests.t()", "a", "b", "app.Owner.save()")),
        ],
    )


FILES = {T1: ["app.OwnerTests"], T2: ["app.ServiceTests"], T3: ["app.PkgOnlyTests"]}


def test_scores_do_not_saturate_and_confidence_labels():
    sel = {c.path: c for c in select_tests(result(), FILES)}
    assert sel[T1].score < 100.0            # graph + name no longer capped to 100
    assert sel[T1].score > sel[T2].score    # closer plus name match ranks higher
    assert sel[T1].confidence == "high"
    assert sel[T2].confidence == "high"
    assert sel[T3].confidence == "low" and sel[T3].score == 10.0


def test_real_centrality():
    srcs = {
        "a/A.java": "package a; public class A { void f() {} }",
        "a/B.java": "package a; public class B { void g() { A a = new A(); a.f(); } }",
        "a/C.java": "package a; public class C { void h() { A a = new A(); a.f(); } }",
    }
    parser = JavaParser()
    files = [parser.parse_source(v.encode(), k) for k, v in srcs.items()]
    graph = DependencyGraph.build(files, Resolver(files).resolve())
    assert direct_dependent_counts(graph, ["a.A.f()", "missing"]) == {"a.A.f()": 2}
