from pathlib import Path

from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from app.schemas.code_symbol import CodeSymbol


class CodeParser:
    def __init__(self, language_name: str):
        self.parser = Parser()
        self.parser.language = get_language(language_name)

    def parse_file(self, file_path: Path):
        source = file_path.read_bytes()
        return self.parser.parse(source)

    def get_root_node(self, file_path: Path):
        tree = self.parse_file(file_path)
        return tree.root_node

    def extract_symbols(self, file_path: Path):
        root = self.get_root_node(file_path)

        symbols = []

        for node in root.children:
            if node.type == "decorated_definition":
                definition = node.child_by_field_name("definition")
                if definition is None:
                    continue
                node = definition

            if node.type not in ("function_definition", "class_definition"):
                continue

            name_node = node.child_by_field_name("name")

            if name_node:
                symbols.append(
                    CodeSymbol(
                        name=name_node.text.decode(),
                        type=node.type,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

        return symbols