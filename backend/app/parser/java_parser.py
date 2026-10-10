import tree_sitter_java
from tree_sitter import Language, Node, Parser

from app.parser.models import (
    ImportInfo,
    ParsedFile,
    ReferenceInfo,
    SymbolInfo,
    TypeRelation,
)

_TYPE_KINDS = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "record_declaration": "record",
}
_METHOD_KINDS = {
    "method_declaration": "method",
    "constructor_declaration": "constructor",
}
_TYPE_KIND_NAMES = set(_TYPE_KINDS.values())


def _text(node: Node | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")


def _line(node: Node) -> int:
    return node.start_point[0] + 1


def _clean_type(text: str) -> str:
    """'Comparable<Greeter>' -> 'Comparable'."""
    return "".join(text.split()).split("<")[0]


class JavaParser:
    def __init__(self) -> None:
        self._parser = Parser(Language(tree_sitter_java.language()))

    def parse_source(self, source: bytes, path: str = "<memory>") -> ParsedFile:
        tree = self._parser.parse(source)
        root = tree.root_node
        result = ParsedFile(path=path, has_syntax_errors=root.has_error)

        if root.has_error:
            self._collect_errors(root, result)

        for child in root.children:
            if child.type == "package_declaration":
                result.package = self._package_name(child)
            elif child.type == "import_declaration":
                result.imports.append(self._import(child))

        self._walk(root, [], result)
        return result

    # ---- header pieces -------------------------------------------------

    def _package_name(self, node: Node) -> str | None:
        for c in node.named_children:
            if c.type in ("scoped_identifier", "identifier"):
                return _text(c)
        return None

    def _import(self, node: Node) -> ImportInfo:
        name = ""
        is_static = False
        is_wildcard = False
        for c in node.children:
            if c.type == "static":
                is_static = True
            elif c.type == "asterisk":
                is_wildcard = True
            elif c.type in ("scoped_identifier", "identifier") and not name:
                name = _text(c)
        return ImportInfo(name, is_static, is_wildcard, _line(node))

    # ---- tree walk -----------------------------------------------------

    def _walk(self, node: Node, scope: list[SymbolInfo], result: ParsedFile) -> None:
        if node.type in _TYPE_KINDS:
            sym = self._declare_type(node, scope, result)
            if sym:
                scope = scope + [sym]
        elif node.type in _METHOD_KINDS:
            sym = self._declare_method(node, scope, result)
            if sym:
                scope = scope + [sym]
        elif node.type == "method_invocation":
            self._add_invocation(node, scope, result)
        elif node.type == "object_creation_expression":
            self._add_instantiation(node, scope, result)

        for child in node.children:
            self._walk(child, scope, result)

    @staticmethod
    def _enclosing_type(scope: list[SymbolInfo]) -> SymbolInfo | None:
        for s in reversed(scope):
            if s.kind in _TYPE_KIND_NAMES:
                return s
        return None

    def _declare_type(self, node, scope, result) -> SymbolInfo | None:
        name = _text(node.child_by_field_name("name"))
        if not name:
            return None
        outer = self._enclosing_type(scope)
        if outer:
            qualified = f"{outer.qualified_name}.{name}"
        elif result.package:
            qualified = f"{result.package}.{name}"
        else:
            qualified = name
        sym = SymbolInfo(
            qualified_name=qualified,
            name=name,
            kind=_TYPE_KINDS[node.type],
            start_line=_line(node),
            end_line=node.end_point[0] + 1,
            parent=outer.qualified_name if outer else None,
        )
        result.symbols.append(sym)
        self._collect_relations(node, qualified, result)
        return sym

    def _declare_method(self, node, scope, result) -> SymbolInfo | None:
        name = _text(node.child_by_field_name("name"))
        outer = self._enclosing_type(scope)
        if not name or outer is None:
            return None
        qualified = f"{outer.qualified_name}.{name}({self._signature(node)})"
        sym = SymbolInfo(
            qualified_name=qualified,
            name=name,
            kind=_METHOD_KINDS[node.type],
            start_line=_line(node),
            end_line=node.end_point[0] + 1,
            parent=outer.qualified_name,
        )
        result.symbols.append(sym)
        return sym

    @staticmethod
    def _signature(node: Node) -> str:
        params = node.child_by_field_name("parameters")
        types: list[str] = []
        if params is not None:
            for p in params.named_children:
                if p.type == "formal_parameter":
                    types.append("".join(_text(p.child_by_field_name("type")).split()))
                elif p.type == "spread_parameter":
                    t = next(
                        (c for c in p.named_children
                         if c.type not in ("modifiers", "variable_declarator")),
                        None,
                    )
                    types.append("".join(_text(t).split()) + "...")
        return ",".join(types)

    # ---- relations, references, errors ---------------------------------

    def _collect_relations(self, node: Node, source: str, result: ParsedFile) -> None:
        for child in node.children:
            if child.type == "superclass":
                kind = "extends"
            elif child.type == "super_interfaces":
                kind = "implements"
            elif child.type == "extends_interfaces":
                kind = "extends"
            else:
                continue
            type_list = next((c for c in child.named_children if c.type == "type_list"), None)
            targets = type_list.named_children if type_list is not None else child.named_children
            for t in targets:
                name = _clean_type(_text(t))
                if name:
                    result.relations.append(TypeRelation(source, name, kind, _line(t)))

    def _add_invocation(self, node: Node, scope, result: ParsedFile) -> None:
        name = _text(node.child_by_field_name("name"))
        if not name:
            return
        receiver = _text(node.child_by_field_name("object")) or None
        result.references.append(
            ReferenceInfo(name, receiver, "invocation", _line(node),
                          scope[-1].qualified_name if scope else None)
        )

    def _add_instantiation(self, node: Node, scope, result: ParsedFile) -> None:
        name = _clean_type(_text(node.child_by_field_name("type")))
        if not name:
            return
        result.references.append(
            ReferenceInfo(name, None, "instantiation", _line(node),
                          scope[-1].qualified_name if scope else None)
        )

    def _collect_errors(self, node: Node, result: ParsedFile) -> None:
        if node.type == "ERROR" or node.is_missing:
            line = _line(node)
            if line not in result.error_lines:
                result.error_lines.append(line)
        for child in node.children:
            if child.has_error or child.is_missing:
                self._collect_errors(child, result)