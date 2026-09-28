from pathlib import Path
from unittest.mock import Mock

import pytest
import responses

from adjacent.__main__ import main, run
from adjacent.github import GitHub, GitHubError
from tests.conftest import BASE, MARKED, readme_response, repository


def discovery(repos=None):
    responses.get(f"{BASE}/repos/owner/target", json=repository())
    responses.get(
        f"{BASE}/users/owner/repos",
        json=repos if repos is not None else [repository("owner/other")],
    )


@responses.activate
def test_entrypoint_idempotence_and_outputs(env, monkeypatch):
    discovery()
    readme_response("owner/target", "statistical inference")
    readme_response("owner/other", "statistical inference")
    monkeypatch.setattr("os.environ", env)
    assert main() == 0
    path = Path(env["GITHUB_WORKSPACE"]) / "README.md"
    first, modified = path.read_bytes(), path.stat().st_mtime_ns
    assert b"owner/other" in first and first.endswith(b"# License\nKeep me.\n")
    assert main() == 0
    assert path.read_bytes() == first and path.stat().st_mtime_ns == modified
    assert (
        Path(env["GITHUB_OUTPUT"]).read_text()
        == "changed=true\nrecommendation_count=1\n"
        "changed=false\nrecommendation_count=1\n"
    )
    assert "Shared topics" in Path(env["GITHUB_STEP_SUMMARY"]).read_text()


@responses.activate
def test_dry_run(env, capsys):
    discovery()
    run(env | {"SIMILARITY_METHOD": "topics", "DRY_RUN": "true"})
    assert (Path(env["GITHUB_WORKSPACE"]) / "README.md").read_bytes() == MARKED
    assert "owner/other" in capsys.readouterr().out
    assert "changed=true" in Path(env["GITHUB_OUTPUT"]).read_text()
    assert len(responses.calls) == 2


@responses.activate
def test_failure_keeps_original(env):
    discovery([repository("owner/one"), repository("owner/two")])
    readme_response("owner/target", "statistics")
    readme_response("owner/one", "statistics")
    responses.get(f"{BASE}/repos/owner/two/readme", status=503)
    with pytest.raises(GitHubError):
        run(env, GitHub("token", sleep=Mock()))
    assert (Path(env["GITHUB_WORKSPACE"]) / "README.md").read_bytes() == MARKED
    assert not Path(env["GITHUB_OUTPUT"]).exists()


def test_markers_validated_before_network(env):
    path = Path(env["GITHUB_WORKSPACE"]) / "README.md"
    path.write_text("no markers")
    client = Mock()
    with pytest.raises(ValueError, match="marker"):
        run(env, client)
    client.repository.assert_not_called()
    assert path.read_text() == "no markers"


@responses.activate
def test_successful_empty_discovery_clears_results(env):
    discovery([])
    run(env | {"SIMILARITY_METHOD": "topics"})
    assert (
        b"No related repositories found."
        in (Path(env["GITHUB_WORKSPACE"]) / "README.md").read_bytes()
    )


@responses.activate
def test_missing_target_readme_uses_topics(env):
    discovery()
    responses.get(f"{BASE}/repos/owner/target/readme", status=404)
    assert run(env)[0].score == 1
    assert len(responses.calls) == 3


@responses.activate
def test_filtered_candidates_not_fetched(env):
    discovery([repository("owner/private", private=True), repository("owner/target")])
    readme_response("owner/target", "stats")
    assert run(env) == []
    assert len(responses.calls) == 3


def test_main_invalid_config_returns_failure(env, monkeypatch, caplog):
    monkeypatch.setattr("os.environ", env | {"MAX_REPOS": "0"})
    assert main() == 1
    assert "MAX_REPOS" in caplog.text
    assert "test-token" not in caplog.text


@responses.activate
def test_module_entrypoint_with_organization_and_custom_path(env, monkeypatch):
    import runpy
    import sys

    root = Path(env["GITHUB_WORKSPACE"])
    custom = root / "docs" / "README.md"
    custom.parent.mkdir()
    custom.write_bytes(MARKED)
    responses.get(
        f"{BASE}/repos/owner/target", json=repository(owner={"type": "Organization"})
    )
    responses.get(f"{BASE}/orgs/owner/repos", json=[repository("owner/other")])
    monkeypatch.setattr(
        "os.environ",
        env | {"README_PATH": "docs/README.md", "SIMILARITY_METHOD": "topics"},
    )
    monkeypatch.delitem(sys.modules, "adjacent.__main__")
    with pytest.raises(SystemExit) as result:
        runpy.run_module("adjacent", run_name="__main__")
    assert result.value.code == 0
    assert b"owner/other" in custom.read_bytes()
    assert (root / "README.md").read_bytes() == MARKED
