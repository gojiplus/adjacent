from unittest.mock import Mock

import pytest
import requests
import responses

from adjacent.github import GitHub, GitHubError
from tests.conftest import BASE, readme_response, repository


@pytest.mark.parametrize(
    "owner_type,endpoint", [("User", "users"), ("Organization", "orgs")]
)
@responses.activate
def test_pagination(owner_type, endpoint):
    first = f"{BASE}/{endpoint}/owner/repos"
    second = first + "?page=2"
    responses.get(
        first,
        json=[repository("owner/one")],
        headers={"Link": f'<{second}>; rel="next"'},
    )
    responses.get(second, json=[repository("owner/two")])
    result = GitHub("token").repositories("owner", owner_type)
    assert len(result) == 2
    assert "per_page=100" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["Authorization"] == "Bearer token"


@responses.activate
def test_repeated_and_untrusted_pagination():
    responses.get(
        f"{BASE}/users/owner/repos",
        json=[],
        headers={"Link": '<https://evil.example/repos>; rel="next"'},
    )
    with pytest.raises(GitHubError, match="host"):
        GitHub("token").repositories("owner", "User")
    assert len(responses.calls) == 1


@pytest.mark.parametrize("status", [401, 403, 404, 422])
@responses.activate
def test_permanent_failure(status):
    responses.get(f"{BASE}/test", status=status)
    with pytest.raises(GitHubError, match=str(status)):
        GitHub("secret").get("/test")
    assert len(responses.calls) == 1


@pytest.mark.parametrize(
    "headers",
    [{"Retry-After": "90"}, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "200"}],
)
@responses.activate
def test_rate_limit(headers):
    responses.get(f"{BASE}/test", status=403, headers=headers)
    responses.get(f"{BASE}/test", json={})
    sleep = Mock()
    GitHub("token", sleep=sleep, now=lambda: 100).get("/test")
    assert sleep.call_args.args[0] >= (90 if "Retry-After" in headers else 101)


@responses.activate
def test_retry_exhaustion_and_large_wait():
    responses.get(f"{BASE}/test", status=503)
    sleep = Mock()
    with pytest.raises(GitHubError, match="budget"):
        GitHub("token", sleep=sleep).get("/test")
    assert len(responses.calls) == 4
    assert sleep.call_count == 3
    responses.get(f"{BASE}/long", status=429, headers={"Retry-After": "900"})
    with pytest.raises(GitHubError, match="five minutes"):
        GitHub("token", sleep=sleep).get("/long")


@responses.activate
def test_timeout_then_success():
    responses.get(f"{BASE}/test", body=requests.Timeout())
    responses.get(f"{BASE}/test", json={})
    sleep = Mock()
    assert GitHub("token", sleep=sleep).get("/test").status_code == 200
    sleep.assert_called_once_with(1)


@responses.activate
def test_missing_and_valid_readme():
    responses.get(f"{BASE}/repos/owner/missing/readme", status=404)
    readme_response("owner/valid", "héllo")
    client = GitHub("token")
    assert client.readme("owner/missing") == ""
    assert client.readme("owner/valid") == "héllo"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"encoding": "base64", "content": "!"},
        {"encoding": "base64", "content": "/w=="},
    ],
)
@responses.activate
def test_invalid_readme(payload):
    responses.get(f"{BASE}/repos/owner/test/readme", json=payload)
    with pytest.raises(GitHubError):
        GitHub("token").readme("owner/test")


@responses.activate
def test_malformed_data():
    responses.get(f"{BASE}/repos/owner/test", body="invalid JSON")
    with pytest.raises(GitHubError, match="JSON"):
        GitHub("token").repository("owner/test")
    responses.get(f"{BASE}/users/owner/repos", json={"message": "wrong"})
    with pytest.raises(GitHubError, match="listing"):
        GitHub("token").repositories("owner", "User")
    with pytest.raises(GitHubError, match="topics"):
        GitHub.validate_repo(repository(topics="not a list"))


@pytest.mark.parametrize(
    "fields",
    [
        {"description": ["not", "text"]},
        {"full_name": "bad\nname"},
        {"owner": {}},
        {"private": "false"},
        {"full_name": "owner/.."},
    ],
)
def test_malformed_metadata(fields):
    with pytest.raises(GitHubError):
        GitHub.validate_repo(repository(**fields))


@responses.activate
def test_pagination_cycle():
    link = f"{BASE}/users/owner/repos?page=2"
    responses.get(
        f"{BASE}/users/owner/repos", json=[], headers={"Link": f'<{link}>; rel="next"'}
    )
    with pytest.raises(GitHubError, match="Repeated"):
        GitHub("token").repositories("owner", "User")


@responses.activate
def test_retries_timeouts_with_explicit_timeout():
    responses.get(f"{BASE}/test", body=requests.Timeout())
    session = requests.Session()
    get = Mock(wraps=session.get)
    session.get = get
    with pytest.raises(GitHubError, match="after retries"):
        GitHub("token", session=session, sleep=Mock()).get("/test")
    assert get.call_count == 4
    assert get.call_args.kwargs["timeout"] == (10, 30)
