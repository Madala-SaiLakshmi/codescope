import pytest

from app.engine.graph import DependencyGraph
from app.engine.resolver import Resolver
from app.parser.java_parser import JavaParser

SOURCES = {
    "app/a/Base.java": "package app.a; public class Base { void inherited() {} }",
    "app/a/A.java": """
        package app.a;
        import app.b.B;
        public class A extends Base {
            void run() { new B(); B.help(); helper(); inherited(); }
            void helper() {}
        }""",
    "app/b/B.java": """
        package app.b;
        import app.a.A;
        public class B { static void help() { new A(); } }""",
    "app/c/C.java": """
        package app.c;
        import app.b.*;
        public class C { void f() { B.help(); } }""",
    "app/d/D.java": """
        package app.d;
        import java.util.ArrayList;
        public class D { void g() { other.thing(); new ArrayList<>(); } }""",
    "app/e/E.java": """
        package app.e;
        public class E {
            void p(int a) {}
            void p(String s) {}
            void q() { p(1); }
        }""",
}

parser = JavaParser()
files = [parser.parse_source(src.encode(), path) for path, src in SOURCES.items()]
edges = Resolver(files).resolve()
graph = DependencyGraph.build(files, edges)


def has(source, target, kind, status="resolved"):
    return any(
        e.source == source and e.target == target and e.kind == kind and e.status == status
        for e in edges
    )


def test_inheritance_resolved():
    assert has("app.a.A", "app.a.Base", "extends")


def test_calls_and_instantiations():
    assert has("app.a.A.run()", "app.b.B", "instantiates")
    assert has("app.a.A.run()", "app.b.B.help()", "calls")
    assert has("app.a.A.run()", "app.a.A.helper()", "calls")
    assert has("app.a.A.run()", "app.a.Base.inherited()", "calls")  # via inheritance
    assert has("app.c.C.f()", "app.b.B.help()", "calls")            # via wildcard import


def test_overloads_are_ambiguous_not_guessed():
    assert has("app.e.E.q()", "app.e.E.p(int)", "calls", "ambiguous")
    assert has("app.e.E.q()", "app.e.E.p(String)", "calls", "ambiguous")
    assert graph.dependencies("app.e.E.q()") == {"app.e.E.p(int)", "app.e.E.p(String)"}
    assert graph.dependencies("app.e.E.q()", include_uncertain=False) == set()


def test_unresolved_and_external_are_reported():
    assert any(e.name == "thing" and e.status == "unresolved" for e in edges)
    assert any(e.name == "ArrayList" and e.status == "external" for e in edges)
    assert "app.d.D" not in graph.dependents("app.a.A")  # nothing invented


def test_reverse_dependencies():
    assert graph.transitive_dependents("app.b.B.help()") == {"app.a.A.run()", "app.c.C.f()"}


def test_transitive_dependencies_and_path():
    assert "app.a.A" in graph.transitive_dependencies("app.c.C.f()")
    assert graph.shortest_path("app.c.C.f()", "app.a.A") == [
        "app.c.C.f()", "app.b.B.help()", "app.a.A",
    ]
    assert graph.explain_impact("app.c.C.f()", "app.a.A") is not None
    assert graph.shortest_path("app.a.Base", "app.c.C") is None


def test_circular_dependency_between_types():
    cycles = graph.collapse_to_types().cycles()
    assert any(set(c) == {"app.a.A", "app.b.B"} for c in cycles)


def test_unknown_node_raises():
    with pytest.raises(KeyError):
        graph.dependencies("does.not.Exist")