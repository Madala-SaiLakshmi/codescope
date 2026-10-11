from app.engine.resolver import Resolver
from app.parser.java_parser import JavaParser

SOURCES = {
    "m/Owner.java": """
        package m;
        public class Owner { public Owner getPet() { return null; } public void save() {} }""",
    "r/Repo.java": """
        package r;
        import m.Owner;
        public class Repo {
            private Owner field;
            void a(Owner p) { p.save(); }
            void b() { Owner l = new Owner(); l.save(); }
            void c() { field.save(); }
            void d() { var v = new Owner(); v.save(); }
            void e(java.util.List<Owner> xs) { for (Owner o : xs) o.save(); }
            void f() { unknown.save(); }
            void g(Owner x) { x.getPet().save(); }
            void h(String field) { field.save(); }
        }""",
    "r/Sub.java": """
        package r;
        public class Sub extends Repo { void s() { field.save(); } }""",
}

parser = JavaParser()
files = [parser.parse_source(s.encode(), p) for p, s in SOURCES.items()]
edges = Resolver(files).resolve()
SAVE = "m.Owner.save()"


def status_of(caller, name):
    return {e.status for e in edges
            if e.source == caller and e.name == name and e.kind == "calls"}


def targets_of(caller, name):
    return {e.target for e in edges
            if e.source == caller and e.name == name and e.status == "resolved"}


def test_parameter_local_field_and_loop_variable_resolve():
    for caller in ("r.Repo.a(Owner)", "r.Repo.b()", "r.Repo.c()",
                   "r.Repo.e(java.util.List<Owner>)"):
        assert targets_of(caller, "save") == {SAVE}, caller


def test_inherited_field_resolves():
    assert targets_of("r.Sub.s()", "save") == {SAVE}


def test_var_and_unknown_stay_unresolved():
    assert status_of("r.Repo.d()", "save") == {"unresolved"}
    assert status_of("r.Repo.f()", "save") == {"unresolved"}


def test_chained_call_resolves_first_hop_only():
    assert targets_of("r.Repo.g(Owner)", "getPet") == {"m.Owner.getPet()"}
    assert status_of("r.Repo.g(Owner)", "save") == {"unresolved"}


def test_parameter_shadows_field():
    assert targets_of("r.Repo.h(String)", "save") == set()
