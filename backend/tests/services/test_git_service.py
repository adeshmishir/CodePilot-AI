import pytest

from app.core.exceptions import RepositoryCloneError
from app.services.github import git_service as module
from app.services.github.git_service import (
    CLONE_FAILED_MESSAGE,
    GitService,
)


def make_service(tmp_path=None):
    directory = tmp_path / "repos" if tmp_path is not None else None
    return GitService(repositories_dir=directory)


def test_extracts_repository_info():
    service = make_service()

    assert service._extract_repository_info(
        "https://github.com/owner/repository"
    ) == ("owner", "repository")


def test_extracts_repository_info_strips_git_suffix():
    service = make_service()

    assert service._extract_repository_info(
        "https://github.com/owner/repository.git"
    ) == ("owner", "repository")


def test_extracts_repository_info_strips_trailing_slash():
    service = make_service()

    assert service._extract_repository_info(
        "https://github.com/owner/repository/"
    ) == ("owner", "repository")


def test_rejects_invalid_url():
    service = make_service()

    with pytest.raises(RepositoryCloneError) as error:
        service._extract_repository_info("not a url at all")

    assert "Invalid repository URL" in str(error.value)


def test_rejects_url_without_owner_and_repo():
    service = make_service()

    with pytest.raises(RepositoryCloneError):
        service._extract_repository_info("https://github.com")


def test_clone_repository_rejects_invalid_url(tmp_path):
    service = make_service(tmp_path)

    with pytest.raises(RepositoryCloneError) as error:
        service.clone_repository("https://github.com")

    assert "Invalid repository URL" in str(error.value)


def test_describes_not_found_error():
    service = make_service()

    error = Exception(
        "remote: Repository not found\nfatal: repository "
        "'https://github.com/owner/nope.git/' not found"
    )

    message = service._describe_clone_error(error)

    assert "does not exist" in message
    assert "renamed" in message


def test_describes_authentication_error():
    service = make_service()

    error = Exception("fatal: could not read Username for 'https://github.com'")

    message = service._describe_clone_error(error)

    assert "authentication is missing or invalid" in message


def test_describes_private_repository_error():
    service = make_service()

    error = Exception("remote: Access denied\nfatal: unable to access ...")

    message = service._describe_clone_error(error)

    assert "authentication is missing or invalid" in message


def test_describes_network_error():
    service = make_service()

    error = Exception("fatal: unable to access 'https://github.com/': Could not resolve host: github.com")

    message = service._describe_clone_error(error)

    assert "Could not connect to GitHub" in message


def test_describes_generic_error():
    service = make_service()

    error = Exception("fatal: some unexpected git failure")

    message = service._describe_clone_error(error)

    assert message == CLONE_FAILED_MESSAGE


def test_redacts_credentials_from_error():
    service = make_service()

    redacted = service._redact_error(
        Exception(
            "fatal: unable to access "
            "'https://octocat:hunter2@github.com/owner/repo.git/'"
        )
    )

    assert "hunter2" not in redacted
    assert "octocat:***" in redacted


def test_remove_repository(tmp_path):
    service = make_service(tmp_path)

    checkout = tmp_path / "repo"
    checkout.mkdir()
    (checkout / "file.txt").write_text("hello")

    service.remove_repository(checkout)

    assert not checkout.exists()
