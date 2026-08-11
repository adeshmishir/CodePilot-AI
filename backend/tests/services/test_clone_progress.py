from app.services.repository.clone_progress import (
    MAX_JOBS,
    CloneProgressStore,
)


def test_start_creates_running_cloning_job():
    store = CloneProgressStore()

    store.start("adeshmishir/CoinOracle")

    job = store.get("adeshmishir/CoinOracle")

    assert job is not None
    assert job.status == "running"
    assert job.phase == "cloning"
    assert job.files_done == 0
    assert job.files_total == 0


def test_update_sets_fields_and_marks_done():
    store = CloneProgressStore()

    store.start("adeshmishir/CoinOracle")
    store.update(
        "adeshmishir/CoinOracle",
        phase="indexing",
        files_done=4,
        files_total=10,
    )
    store.update(
        "adeshmishir/CoinOracle",
        status="done",
        message="Done.",
        repository_id=7,
    )

    job = store.get("adeshmishir/CoinOracle")

    assert job.phase == "indexing"
    assert job.files_done == 4
    assert job.files_total == 10
    assert job.status == "done"
    assert job.message == "Done."
    assert job.repository_id == 7


def test_get_returns_copy_not_mutable_reference():
    store = CloneProgressStore()

    store.start("owner/repo")

    job = store.get("owner/repo")
    job.status = "done"

    assert store.get("owner/repo").status == "running"


def test_update_unknown_job_is_noop():
    store = CloneProgressStore()

    store.update("missing/job", status="done")

    assert store.get("missing/job") is None


def test_is_running():
    store = CloneProgressStore()

    store.start("owner/repo")
    assert store.is_running("owner/repo") is True

    store.update("owner/repo", status="done")
    assert store.is_running("owner/repo") is False

    assert store.is_running("missing/job") is False


def test_prunes_expired_jobs():
    store = CloneProgressStore()

    store.start("old/job")
    job = store.get("old/job")
    store.update("old/job", updated_at=job.updated_at - 2 * 60 * 60)

    store.start("new/job")

    assert store.get("old/job") is None
    assert store.get("new/job") is not None


def test_caps_number_of_jobs():
    store = CloneProgressStore()

    for index in range(MAX_JOBS + 20):
        store.start(f"owner/repo{index}")

    assert len(store.get_all_ids()) <= MAX_JOBS


def test_get_all_ids_returns_current_jobs():
    store = CloneProgressStore()

    store.start("a/one")
    store.start("b/two")

    assert sorted(store.get_all_ids()) == ["a/one", "b/two"]
