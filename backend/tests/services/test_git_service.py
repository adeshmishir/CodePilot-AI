import pytest

from app.config.settings import settings
from app.core.exceptions import RepositoryCloneError
from app.services.github import git_service as module
from app.services.github.git_service import (
    AUTH_FAILED_MESSAGE,
    CLONE_FAILED_MESSAGE,
    GitService,
)


def make_service(tmp_path=None):
    directory = tmp_path / "repos" if tmp_path is not None else None
    return GitService(repositories_dir=directory)


def make_clone_spy(monkeypatch, error=None):
    captured = {}

    def fake_clone(url, to_path, **kwargs):
        captured["url"] = url
        captured["env"] = kwargs.get("env")
        captured["depth"] = kwargs.get("depth")
        if error is not None:
            raise error

    monkeypatch.setattr(module.Repo, "clone_from", staticmethod(fake_clone))

    return captured


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


def test_describes_fine_grained_token_missing_repository_access():
    service = make_service()

    error = Exception(
        "remote: Write access to repository not granted.\n"
        "fatal: unable to access "
        "'https://github.com/owner/repo.git/': The requested URL returned "
        "error: 403"
    )

    message = service._describe_clone_error(error)

    assert message == AUTH_FAILED_MESSAGE


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


def test_public_clone_without_token_uses_anonymous_url(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    result = service.clone_repository("https://github.com/owner/public-repo")

    assert result["success"] is True
    assert captured["url"] == "https://github.com/owner/public-repo"
    assert captured["env"] == {"GIT_TERMINAL_PROMPT": "0"}


def test_private_clone_uses_token_and_noninteractive_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_secret_token")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository("https://github.com/owner/private-repo")

    assert captured["url"] == (
        "https://x-access-token:ghp_secret_token@github.com/"
        "owner/private-repo.git"
    )
    assert captured["env"] == {"GIT_TERMINAL_PROMPT": "0"}


def test_token_is_url_encoded_in_clone_url(tmp_path, monkeypatch):
    from urllib.parse import unquote

    token = "ghp_secret token/with@chars"
    monkeypatch.setattr(settings, "GITHUB_TOKEN", token)
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository("https://github.com/owner/repo")

    assert "x-access-token:" in captured["url"]
    assert "ghp_secret" in captured["url"]
    assert "token/with@chars" not in captured["url"]
    assert token in unquote(captured["url"])


def test_token_not_used_for_non_github_host(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_secret_token")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository("https://gitlab.com/owner/repo")

    assert captured["url"] == "https://gitlab.com/owner/repo"


def test_private_clone_missing_token_returns_auth_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    make_clone_spy(
        monkeypatch,
        error=Exception(
            "Cmd('git') failed due to: exit code(128)\n"
            "stderr: fatal: could not read Username for "
            "'https://github.com': No such device or address"
        ),
    )

    with pytest.raises(RepositoryCloneError) as error:
        service.clone_repository("https://github.com/owner/private-repo")

    assert error.value.message == AUTH_FAILED_MESSAGE


def test_private_clone_invalid_token_returns_auth_error(tmp_path, monkeypatch):
    token = "ghp_invalid_token"
    monkeypatch.setattr(settings, "GITHUB_TOKEN", token)
    service = make_service(tmp_path)

    make_clone_spy(
        monkeypatch,
        error=Exception(
            "fatal: Authentication failed for "
            f"'https://x-access-token:{token}@github.com/"
            "owner/private-repo.git/'"
        ),
    )

    with pytest.raises(RepositoryCloneError) as error:
        service.clone_repository("https://github.com/owner/private-repo")

    assert error.value.message == AUTH_FAILED_MESSAGE
    assert token not in error.value.detail
    assert "x-access-token:***" in error.value.detail


def test_token_never_leaks_in_error_detail(tmp_path, monkeypatch):
    token = "ghp_super_secret_value"
    monkeypatch.setattr(settings, "GITHUB_TOKEN", token)
    service = make_service(tmp_path)

    make_clone_spy(
        monkeypatch,
        error=Exception(
            "Cmd('git') failed due to: exit code(128)\n"
            "cmdline: git clone -v -- "
            f"'https://x-access-token:{token}@github.com/owner/repo.git'\n"
            "stderr: fatal: unable to access "
            f"'https://x-access-token:{token}@github.com/owner/repo.git/': "
            "The requested URL returned error: 500"
        ),
    )

    with pytest.raises(RepositoryCloneError) as error:
        service.clone_repository("https://github.com/owner/repo")

    assert token not in error.value.detail
    assert token not in error.value.message
    assert "x-access-token:***" in error.value.detail


def test_failed_clone_cleans_partial_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    def fake_clone(url, to_path, **kwargs):
        checkout = tmp_path / "repos" / "owner" / "repo"
        checkout.mkdir(parents=True, exist_ok=True)
        (checkout / ".git").mkdir(exist_ok=True)
        (checkout / "partial.txt").write_text("partial")
        raise RuntimeError("boom")

    monkeypatch.setattr(module.Repo, "clone_from", staticmethod(fake_clone))

    with pytest.raises(RepositoryCloneError):
        service.clone_repository("https://github.com/owner/repo")

    assert not (tmp_path / "repos" / "owner" / "repo").exists()


def test_recover_repository_uses_token(tmp_path, monkeypatch):
    token = "ghp_recover_token"
    monkeypatch.setattr(settings, "GITHUB_TOKEN", token)
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    result = service.recover_repository("https://github.com/owner/broken-repo")

    assert result["success"] is True
    assert captured["url"] == (
        "https://x-access-token:ghp_recover_token@github.com/"
        "owner/broken-repo.git"
    )


def test_recover_repository_without_token_clones_anonymously(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.recover_repository("https://github.com/owner/broken-repo")

    assert captured["url"] == "https://github.com/owner/broken-repo"


def test_clone_existing_valid_repository_skips_clone(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_token")
    service = make_service(tmp_path)

    checkout = tmp_path / "repos" / "owner" / "repo"
    checkout.mkdir(parents=True)
    (checkout / ".git").mkdir()

    captured = make_clone_spy(monkeypatch)

    result = service.clone_repository("https://github.com/owner/repo")

    assert result["message"] == "Repository already exists"
    assert captured == {}


def test_recover_existing_healthy_repository_skips_clone(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_token")
    service = make_service(tmp_path)

    checkout = tmp_path / "repos" / "owner" / "repo"
    checkout.mkdir(parents=True)
    (checkout / ".git").mkdir()

    captured = make_clone_spy(monkeypatch)

    result = service.recover_repository("https://github.com/owner/repo")

    assert result["message"] == "Repository already exists"
    assert captured == {}


def test_redacts_token_value_in_error(tmp_path, monkeypatch):
    token = "ghp_raw_secret_value"
    monkeypatch.setattr(settings, "GITHUB_TOKEN", token)
    service = make_service(tmp_path)

    redacted = service._redact_error(
        Exception(f"fatal: unexpected {token} in output")
    )

    assert token not in redacted


def test_github_clone_uses_shallow_depth(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository("https://github.com/owner/repo")

    assert captured["depth"] == 1
    assert captured["env"] == {"GIT_TERMINAL_PROMPT": "0"}


def test_github_private_clone_uses_shallow_depth(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_secret_token")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository("https://github.com/owner/private-repo")

    assert captured["depth"] == 1
    assert "x-access-token:" in captured["url"]


def test_recover_repository_uses_shallow_depth(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_recover_token")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.recover_repository("https://github.com/owner/broken-repo")

    assert captured["depth"] == 1


def test_non_github_clone_is_not_shallow(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository("https://gitlab.com/owner/repo")

    assert captured["url"] == "https://gitlab.com/owner/repo"
    assert captured["depth"] is None


def test_local_path_clone_is_not_shallow(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    service = make_service(tmp_path)

    captured = make_clone_spy(monkeypatch)

    service.clone_repository((tmp_path / "some" / "repo").as_posix())

    assert captured["depth"] is None
