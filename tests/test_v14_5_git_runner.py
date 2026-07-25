"""
Test v14.5: Git Operations Step-Runner
"""
import subprocess
import pytest
from buster.autonomy.executors.git_runner import GitOperationRunner


@pytest.fixture
def temp_git_repo(tmp_path):
    """Initializes a temporary git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Configure local git user and init
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Bot"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "bot@test.local"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    file1 = repo / "init.txt"
    file1.write_text("initial", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)

    return repo


def test_git_status_and_commit(temp_git_repo):
    runner = GitOperationRunner()

    # 1. Clean repo status
    status = runner.get_status(temp_git_repo)
    assert status["status"] == "success"
    assert status["has_changes"] is False

    # 2. Modify file
    (temp_git_repo / "new_file.txt").write_text("content", encoding="utf-8")

    status_after = runner.get_status(temp_git_repo)
    assert status_after["has_changes"] is True

    # 3. Commit change
    commit_res = runner.create_commit(
        repo_path=temp_git_repo,
        message="auto: add new_file.txt",
    )
    assert commit_res["status"] == "success"

    # 4. Confirm clean status again
    status_final = runner.get_status(temp_git_repo)
    assert status_final["has_changes"] is False