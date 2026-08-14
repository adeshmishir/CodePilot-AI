from pathlib import Path

from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from app.schemas.code_chunk import CodeChunk
from app.schemas.code_symbol import CodeSymbol
from app.services.parser.language_mapper import get_language_from_path


SYMBOL_NODE_TYPES = {
    "function_definition",
    "class_definition",
    "function_declaration",
    "generator_function_declaration",
    "class_declaration",
    "method_definition",
    "method_declaration",
    "constructor_declaration",
    "interface_declaration",
    "type_alias_declaration",
    "enum_declaration",
    "type_spec",
    "function_item",
    "struct_item",
    "enum_item",
    "trait_item",
    "struct_specifier",
    "class_specifier",
    "property_declaration",
    "struct_declaration",
    "protocol_declaration",
}

ANONYMOUS_FUNCTION_TYPES = {
    "arrow_function",
    "anonymous_function",
    "lambda",
}


class CodeParser:
    def __init__(self):
        self.parser = Parser()

    def parse_file(self, file_path: Path):
        from app.services.parser.language_mapper import get_language_from_path

        language_name = get_language_from_path(file_path)

        if language_name is None:
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}"
            )

        self.parser.language = get_language(language_name)

        source = file_path.read_bytes()

        return self.parser.parse(source)

    def get_root_node(self, file_path: Path):
        tree = self.parse_file(file_path)
        return tree.root_node

    def _extract_name(self, node):
        name_node = node.child_by_field_name("name")

        if name_node is not None:
            return name_node.text.decode()

        if node.type in ANONYMOUS_FUNCTION_TYPES:
            parent = node.parent

            while parent is not None:
                if parent.type in (
                    "variable_declarator",
                    "assignment_left",
                    "field_definition",
                ):
                    name_node = parent.child_by_field_name("name")

                    if name_node is not None:
                        return name_node.text.decode()

                parent = parent.parent

        return None

    def _symbols_from_root(self, root) -> list[CodeSymbol]:
        symbols = []

        def visit(node):
            if (
                node.type in SYMBOL_NODE_TYPES
                or node.type in ANONYMOUS_FUNCTION_TYPES
            ):
                name = self._extract_name(node)

                if name:
                    symbols.append(
                        CodeSymbol(
                            name=name,
                            type=node.type,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                        )
                    )

            for child in node.children:
                visit(child)

        visit(root)

        unique_symbols = []
        seen = set()

        for symbol in symbols:
            key = (
                symbol.name,
                symbol.type,
                symbol.start_line,
                symbol.end_line,
            )

            if key not in seen:
                seen.add(key)
                unique_symbols.append(symbol)

        return unique_symbols

    def extract_symbols(self, file_path: Path):
        root = self.get_root_node(file_path)
        return self._symbols_from_root(root)

    def create_chunks(self, file_path: Path):
        language_name = get_language_from_path(file_path)

        if language_name is None:
            return self._create_doc_chunks(file_path)

        # Read the source bytes once and reuse them for both the AST parse
        # and the chunk contents. Reading the file twice (once as bytes for
        # tree-sitter and again via read_text()) doubles the per-file peak
        # memory, which matters when hundreds of files are indexed back to
        # back on a small instance.
        self.parser.language = get_language(language_name)

        source_bytes = file_path.read_bytes()

        source_lines = source_bytes.decode("utf-8", errors="replace").splitlines()

        tree = self.parser.parse(source_bytes)

        # The symbol objects are independent of the tree and the bytes, so
        # release both as soon as the traversal is done.
        symbols = self._symbols_from_root(tree.root_node)
        del tree
        del source_bytes

        chunks = []

        for symbol in symbols:
            content = "\n".join(
                source_lines[
                    symbol.start_line - 1 : symbol.end_line
                ]
            )

            chunks.append(
                CodeChunk(
                    file_path=str(file_path),
                    symbol_name=symbol.name,
                    symbol_type=symbol.type,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    content=content,
                )
            )

        return chunks

    def _create_doc_chunks(
        self,
        file_path: Path,
        chunk_lines: int = 80,
    ):
        """Chunk documentation files (e.g. README.md) by line ranges.

        Docs have no code symbols, so each chunk is a plain line window.
        This lets the RAG pipeline answer "what is this project" style
        questions that previously returned insufficient context.
        """
        source_text = file_path.read_text()

        if "\x00" in source_text:
            return []

        source_lines = source_text.splitlines()

        chunks = []

        for start in range(0, len(source_lines), chunk_lines):
            end = min(start + chunk_lines, len(source_lines))

            chunks.append(
                CodeChunk(
                    file_path=str(file_path),
                    symbol_name="documentation",
                    symbol_type="documentation",
                    start_line=start + 1,
                    end_line=end,
                    content="\n".join(source_lines[start:end]),
                )
            )

        return chunks
