import pytest

from pathlib import Path

from app.config.settings import settings
from app.services.parser.repository_parser import RepositoryParser


SAMPLE = "def hello(name):\n    return f'Hello, {name}'\n"


def write_file(repo, relative, content=SAMPLE):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def file_names(files):
    return {path.name for path in files}


def test_supported_source_files_are_discovered(tmp_path):
    parser = RepositoryParser()

    write_file(tmp_path, "src/a.py")
    write_file(tmp_path, "src/b.js")
    write_file(tmp_path, "README.md")
    write_file(tmp_path, "notes.xyz")

    files = parser.get_repository_files(tmp_path)

    assert file_names(files) == {"a.py", "b.js", "README.md"}


def test_common_web_and_config_extensions_are_discovered(tmp_path):
    parser = RepositoryParser()

    write_file(tmp_path, "ui/App.jsx")
    write_file(tmp_path, "ui/styles.css")
    write_file(tmp_path, "index.html")
    write_file(tmp_path, "pages/index.vue")
    write_file(tmp_path, "config.yaml")
    write_file(tmp_path, "main.rs")
    write_file(tmp_path, "script.sh")

    files = parser.get_repository_files(tmp_path)

    assert file_names(files) == {
        "App.jsx",
        "styles.css",
        "index.html",
        "index.vue",
        "config.yaml",
        "main.rs",
        "script.sh",
    }


def test_lockfiles_and_minified_files_are_skipped(tmp_path):
    parser = RepositoryParser()

    write_file(tmp_path, "package-lock.json", "{}")
    write_file(tmp_path, "yarn.lock", "yarn lock contents")
    write_file(tmp_path, "static/vendor.min.js", "var a=1;")
    write_file(tmp_path, "static/vendor.min.css", ".a{color:red}")
    kept = write_file(tmp_path, "src/kept.py")

    files = parser.get_repository_files(tmp_path)

    assert files == [kept]


def test_max_index_files_cap_bounds_file_count(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAX_INDEX_FILES", 2)

    parser = RepositoryParser()

    write_file(tmp_path, "a.py")
    write_file(tmp_path, "b.py")
    write_file(tmp_path, "c.py")

    files = parser.get_repository_files(tmp_path)

    assert len(files) == 2


@pytest.mark.parametrize(
    "directory",
    [
        ".git",
        ".github",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".cache",
        ".next",
        ".nuxt",
        ".output",
        "coverage",
    ],
)
def test_ignored_directories_are_skipped(tmp_path, directory):
    parser = RepositoryParser()

    write_file(tmp_path, f"{directory}/ignored.py")
    kept = write_file(tmp_path, "src/kept.py")

    files = parser.get_repository_files(tmp_path)

    assert files == [kept]


def test_coverage_file_extension_is_skipped(tmp_path):
    parser = RepositoryParser()

    write_file(tmp_path, ".coverage", "ignored")

    files = parser.get_repository_files(tmp_path)

    assert files == []


def test_large_files_are_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAX_INDEX_FILE_SIZE_MB", 0.001)

    parser = RepositoryParser()

    write_file(tmp_path, "big.py", "x" * 2048)
    small = write_file(tmp_path, "src/small.py", "y" * 512)

    files = parser.get_repository_files(tmp_path)

    assert files == [small]


def test_binary_files_are_skipped(tmp_path):
    parser = RepositoryParser()

    binary = tmp_path / "generated.py"
    binary.write_bytes(b"\x00\x01\x02" + b"not really source code")

    text = write_file(tmp_path, "src/text.py")

    files = parser.get_repository_files(tmp_path)

    assert files == [text]


def test_missing_file_size_does_not_break_discovery(tmp_path, monkeypatch):
    parser = RepositoryParser()

    write_file(tmp_path, "src/kept.py")

    original_stat = Path.stat

    def failing_stat(self, *args, **kwargs):
        if self.name == "kept.py":
            raise OSError("stat failed")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", failing_stat)

    files = parser.get_repository_files(tmp_path)

    assert files == []
