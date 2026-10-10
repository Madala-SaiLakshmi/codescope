from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImportInfo:
    name: str          # "java.util.List"; for wildcards the package, e.g. "java.io"
    is_static: bool
    is_wildcard: bool
    line: int


@dataclass(frozen=True)
class SymbolInfo:
    qualified_name: str   # "com.example.Greeter.greet(String)"
    name: str
    kind: str             # class | interface | enum | record | method | constructor
    start_line: int       # 1-based
    end_line: int
    parent: str | None    # qualified name of the enclosing type


@dataclass(frozen=True)
class TypeRelation:
    source: str           # qualified name of the declaring type
    target: str           # name as written in source (NOT yet resolved)
    kind: str             # "extends" | "implements"
    line: int


@dataclass(frozen=True)
class ReferenceInfo:
    name: str             # method name, or the type name for "new Foo()"
    receiver: str | None  # text before the dot, e.g. "helper" or "System.out"
    kind: str             # "invocation" | "instantiation"
    line: int
    caller: str | None    # qualified name of the enclosing method/type


@dataclass
class ParsedFile:
    path: str
    package: str | None = None
    imports: list[ImportInfo] = field(default_factory=list)
    symbols: list[SymbolInfo] = field(default_factory=list)
    relations: list[TypeRelation] = field(default_factory=list)
    references: list[ReferenceInfo] = field(default_factory=list)
    has_syntax_errors: bool = False
    error_lines: list[int] = field(default_factory=list)


@dataclass
class ScanResult:
    files: list[ParsedFile] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (path, reason)