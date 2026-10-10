from app.parser.java_parser import JavaParser
from app.parser.scanner import scan_java_files

SAMPLE = b"""
package com.example;

import java.util.List;
import static java.lang.Math.max;
import java.io.*;

public class Greeter extends Base implements Runnable, Comparable<Greeter> {
    private final Helper helper = new Helper();

    public Greeter() {
        super();
    }

    public String greet(String name) {
        return helper.format(name);
    }

    public String greet(String name, int times) {
        return greet(name);
    }

    public void run() {}

    static class Inner {
        void ping() { System.out.println("x"); }
    }
}

interface Shape extends Drawable { double area(); }
enum Color { RED, GREEN }
record Point(int x, int y) {}
"""

parser = JavaParser()
parsed = parser.parse_source(SAMPLE, "Greeter.java")


def test_package_and_imports():
    assert parsed.package == "com.example"
    by_name = {i.name: i for i in parsed.imports}
    assert "java.util.List" in by_name
    assert by_name["java.lang.Math.max"].is_static
    assert by_name["java.io"].is_wildcard


def test_symbols_and_overloads():
    names = {s.qualified_name for s in parsed.symbols}
    assert {
        "com.example.Greeter",
        "com.example.Greeter.Greeter()",
        "com.example.Greeter.greet(String)",
        "com.example.Greeter.greet(String,int)",
        "com.example.Greeter.Inner",
        "com.example.Greeter.Inner.ping()",
        "com.example.Shape",
        "com.example.Shape.area()",
        "com.example.Color",
        "com.example.Point",
    } <= names


def test_symbol_kinds_and_lines():
    kinds = {s.qualified_name: s.kind for s in parsed.symbols}
    assert kinds["com.example.Shape"] == "interface"
    assert kinds["com.example.Color"] == "enum"
    assert kinds["com.example.Point"] == "record"
    assert kinds["com.example.Greeter.Greeter()"] == "constructor"
    greeter = next(s for s in parsed.symbols if s.qualified_name == "com.example.Greeter")
    assert greeter.start_line < greeter.end_line


def test_inheritance_relations():
    rels = {(r.source, r.target, r.kind) for r in parsed.relations}
    assert ("com.example.Greeter", "Base", "extends") in rels
    assert ("com.example.Greeter", "Runnable", "implements") in rels
    assert ("com.example.Greeter", "Comparable", "implements") in rels
    assert ("com.example.Shape", "Drawable", "extends") in rels


def test_references():
    refs = {(r.caller, r.name, r.receiver, r.kind) for r in parsed.references}
    assert ("com.example.Greeter.greet(String)", "format", "helper", "invocation") in refs
    assert ("com.example.Greeter.greet(String,int)", "greet", None, "invocation") in refs
    assert ("com.example.Greeter.Inner.ping()", "println", "System.out", "invocation") in refs
    assert any(r.name == "Helper" and r.kind == "instantiation" for r in parsed.references)


def test_syntax_error_is_reported_not_raised():
    broken = parser.parse_source(b"class A { void f( { }", "Broken.java")
    assert broken.has_syntax_errors
    assert broken.error_lines


def test_empty_source():
    empty = parser.parse_source(b"", "Empty.java")
    assert empty.symbols == [] and not empty.has_syntax_errors


def test_scanner_skips_noise(tmp_path):
    (tmp_path / "A.java").write_text("class A {}")
    (tmp_path / "notes.txt").write_text("hi")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "B.java").write_text("class B {}")
    result = scan_java_files(tmp_path)
    assert [f.path for f in result.files] == ["A.java"]