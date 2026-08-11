import os
import shutil
import subprocess

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import RepositoryIndexError
from app.database.base import Base
from app.models.repository import RepositoryModel
from app.services.github.git_service import git_service
from app.services.repository.paths import normalize_local_path
from app.services.repository.repository_service import RepositoryService


def make_git_repo(path, files):
    path.mkdir(parents=True, exist_ok=True)

    for relative, content in files.items():
        file_path = path / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "init"],
        check=True,
        env=env,
    )


def force_rmtree(path):
    if os.name == "nt":
        for root, _, files in os.walk(path):
            for name in files:
                os.chmod(os.path.join(root, name), 0o666)

    shutil.rmtree(path, ignore_errors=True)


SOURCE_FILES = {
    "src/app.py": (
        "def hello(name):\n"
        "    return f'Hello, {name}'\n"
        "\n"
        "\n"
        "class Greeter:\n"
        "    def greet(self):\n"
        "        return hello('world')\n"
    ),
    "src/utils.py": (
        "def add(a, b):\n"
        "    return a + b\n"
    ),
}


class FakeEmbeddingService:
    def embed(self, text):
        return [0.5] * 384


class FakeVectorStore:
    def __init__(self):
        self.upserted = []

    def create_collection(self):
        pass

    def delete_repository_points(self, repository_id):
        pass

    def upsert_embedding(self, point_id, vector, payload):
        self.upserted.append(
            {
                "point_id": point_id,
                "payload": payload,
            }
        )


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    yield session
    session.close()


@pytest.fixture
def clone_root(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.embedding.embedding_service.EmbeddingService",
        FakeEmbeddingService,
    )

    monkeypatch.setattr(
        "app.services.vector.vector_store.VectorStore",
        FakeVectorStore,
    )

    monkeypatch.setattr(
        "app.services.vector.vector_store.get_vector_store",
        lambda: FakeVectorStore(),
    )

    root = tmp_path / "clone_root"

    monkeypatch.setattr(git_service, "repositories_dir", root)

    return root


def make_source(tmp_path):
    """Create a git repo whose URL resolves to someowner/somename."""
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(source, SOURCE_FILES)
    return source


def add_repository(db, clone_url, local_path):
    repository = RepositoryModel(
        owner="someowner",
        name="somename",
        clone_url=clone_url,
        local_path=local_path,
    )

    db.add(repository)
    db.commit()
    db.refresh(repository)

    return repository


def test_index_repository_clones_and_indexes(
    tmp_path,
    db,
    clone_root,
):
    source = make_source(tmp_path)

    repository = add_repository(
        db,
        source.as_posix(),
        "data/repos/someowner/somename",
    )

    result = RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    assert result["files_discovered"] == 2
    assert result["chunks_created"] >= 2
    assert result["vectors_indexed"] == result["chunks_created"]

    clone_path = clone_root / "someowner" / "somename"

    assert clone_path.is_dir()
    assert (clone_path / ".git").is_dir()


def test_index_repository_recovers_missing_clone_from_clone_url(
    tmp_path,
    db,
    clone_root,
):
    source = make_source(tmp_path)

    repository = add_repository(
        db,
        source.as_posix(),
        "data/repos/someowner/somename",
    )

    RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    clone_path = clone_root / "someowner" / "somename"
    force_rmtree(clone_path)

    assert not clone_path.exists()

    result = RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    assert clone_path.is_dir()
    assert (clone_path / ".git").is_dir()
    assert result["files_discovered"] == 2
    assert result["chunks_created"] >= 2


def test_index_repository_normalizes_windows_local_path(
    tmp_path,
    db,
    clone_root,
):
    source = make_source(tmp_path)

    repository = add_repository(
        db,
        source.as_posix(),
        "data\\repos\\someowner\\somename",
    )

    result = RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    assert result["files_discovered"] == 2
    assert "\\" not in repository.local_path

    resolved = normalize_local_path(repository.local_path)
    assert resolved.is_dir()
    assert (resolved / ".git").is_dir()


def test_index_repository_raises_when_repository_missing(
    db,
    clone_root,
):
    with pytest.raises(RepositoryIndexError):
        RepositoryService().index_repository(
            repository_id=9999,
            repository_path="data/repos/owner/name",
            db=db,
        )


def test_index_repository_raises_when_unrecoverable(
    tmp_path,
    db,
    clone_root,
):
    repository = add_repository(db, "", "data/repos/someowner/somename")

    with pytest.raises(RepositoryIndexError) as error:
        RepositoryService().index_repository(
            repository_id=repository.id,
            repository_path=repository.local_path,
            db=db,
        )

    assert "cannot be recovered" in str(error.value)


def test_index_repository_raises_when_no_source_files(
    tmp_path,
    db,
    clone_root,
):
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "README.md": "# documentation only",
        },
    )

    repository = add_repository(
        db,
        source.as_posix(),
        "data/repos/someowner/somename",
    )

    with pytest.raises(RepositoryIndexError) as error:
        RepositoryService().index_repository(
            repository_id=repository.id,
            repository_path=repository.local_path,
            db=db,
        )

    assert "No supported source files" in str(error.value)
