from pathlib import Path

SAMPLE_SOURCES = {
    "app/a/A.java": """
        package app.a;
        import app.b.B;
        public class A { void run() { B.help(); } }""",
    "app/b/B.java": """
        package app.b;
        import app.a.A;
        public class B { static void help() { new A(); } }""",
    "app/c/C.java": """
        package app.c;
        import app.b.B;
        public class C { void f() { B.help(); } }""",
}


def write_sample(dest: Path) -> None:
    for rel, src in SAMPLE_SOURCES.items():
        p = Path(dest) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
