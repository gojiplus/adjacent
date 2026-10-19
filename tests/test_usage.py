import json
from unittest.mock import Mock

import pytest
import responses

from adjacent.github import GitHub, GitHubError
from adjacent.usage import update_counts


@responses.activate
def test_rate_limit_retry_keeps_the_existing_badge_shape(tmp_path):
    responses.get(
        "https://api.github.com/search/code", status=429, headers={"Retry-After": "61"}
    )
    responses.get("https://api.github.com/search/code", json={"total_count": 12345})
    sleep = Mock()
    update_counts(GitHub("test", sleep=sleep), tmp_path, ["o/action"])
    sleep.assert_called_once_with(61.0)
    badge = json.loads((tmp_path / "action.json").read_text())
    assert badge["message"] == "12.3K"
    assert badge["schemaVersion"] == 1


@responses.activate
def test_failed_query_preserves_all_previous_counts(tmp_path):
    (tmp_path / "one.json").write_text("previous")
    responses.get("https://api.github.com/search/code", json={"total_count": 2})
    responses.get("https://api.github.com/search/code", status=401)
    with pytest.raises(GitHubError, match="401"):
        update_counts(GitHub("test"), tmp_path, ["o/one", "o/two"], sleep=Mock())
    assert (tmp_path / "one.json").read_text() == "previous"
    assert not (tmp_path / "two.json").exists()


@responses.activate
def test_incomplete_search_is_not_published(tmp_path):
    responses.get(
        "https://api.github.com/search/code",
        json={"total_count": 5, "incomplete_results": True},
    )
    with pytest.raises(GitHubError, match="incomplete"):
        update_counts(GitHub("test"), tmp_path, ["o/one"])
    assert not list(tmp_path.iterdir())
