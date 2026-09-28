import base64
import time
from urllib.parse import urlparse

import requests

from adjacent.config import valid_repository


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token, session=None, sleep=time.sleep, now=time.time):
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2026-03-10",
            }
        )
        self.sleep = sleep
        self.now = now

    def get(self, path, missing_ok=False):
        url = path if path.startswith("https://") else f"https://api.github.com{path}"
        if urlparse(url).netloc != "api.github.com":
            raise GitHubError("Unexpected API pagination host")
        for attempt in range(4):
            try:
                response = self.session.get(url, timeout=(10, 30))
            except (requests.Timeout, requests.ConnectionError):
                if attempt == 3:
                    raise GitHubError("GitHub request failed after retries") from None
                self.sleep(2**attempt)
                continue
            if missing_ok and response.status_code == 404:
                return None
            if response.status_code == 200:
                return response
            limited = response.status_code == 429 or (
                response.status_code == 403
                and (
                    response.headers.get("X-RateLimit-Remaining") == "0"
                    or "Retry-After" in response.headers
                    or "secondary rate limit" in response.text.lower()
                )
            )
            if not limited and response.status_code not in {500, 502, 503, 504}:
                raise GitHubError(f"GitHub returned HTTP {response.status_code}")
            if attempt == 3:
                raise GitHubError("GitHub retry budget exhausted")
            delay = 60 * (2**attempt) if limited else 2**attempt
            try:
                if "Retry-After" in response.headers:
                    delay = max(delay, float(response.headers["Retry-After"]))
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    delay = max(
                        delay,
                        float(response.headers["X-RateLimit-Reset"]) - self.now() + 1,
                    )
            except (ValueError, KeyError):
                raise GitHubError("Invalid GitHub rate-limit headers") from None
            if delay > 300:
                raise GitHubError(
                    "GitHub rate-limit wait exceeds five minutes; retry later"
                )
            self.sleep(delay)
        raise GitHubError("GitHub request failed")

    @staticmethod
    def json(response):
        try:
            return response.json()
        except ValueError:
            raise GitHubError("GitHub returned invalid JSON") from None

    def repository(self, full_name):
        data = self.json(self.get(f"/repos/{full_name}"))
        self.validate_repo(data)
        return data

    @staticmethod
    def validate_repo(data):
        if not isinstance(data, dict) or not valid_repository(data.get("full_name")):
            raise GitHubError("Malformed repository metadata")
        if data.get("description") is not None and not isinstance(
            data["description"], str
        ):
            raise GitHubError("Malformed repository description")
        if not isinstance(data.get("topics"), list) or not all(
            isinstance(t, str) for t in data["topics"]
        ):
            raise GitHubError("Malformed repository topics")
        if not isinstance(data.get("owner"), dict) or data["owner"].get("type") not in {
            "User",
            "Organization",
        }:
            raise GitHubError("Malformed repository owner")
        for key in ("private", "archived", "disabled", "fork", "is_template"):
            if not isinstance(data.get(key), bool):
                raise GitHubError(f"Malformed repository field: {key}")

    def repositories(self, owner, owner_type):
        endpoint = "orgs" if owner_type == "Organization" else "users"
        kind = "public" if endpoint == "orgs" else "owner"
        url = f"/{endpoint}/{owner}/repos?per_page=100&type={kind}"
        repos, seen = [], set()
        while url:
            if url in seen:
                raise GitHubError("Repeated pagination link")
            seen.add(url)
            response = self.get(url)
            page = self.json(response)
            if not isinstance(page, list):
                raise GitHubError("Malformed repository listing")
            for repo in page:
                self.validate_repo(repo)
            repos.extend(page)
            url = response.links.get("next", {}).get("url")
        return repos

    def readme(self, full_name):
        response = self.get(f"/repos/{full_name}/readme", missing_ok=True)
        if response is None:
            return ""
        data = self.json(response)
        if (
            not isinstance(data, dict)
            or data.get("encoding") != "base64"
            or not isinstance(data.get("content"), str)
        ):
            raise GitHubError("Malformed README response")
        try:
            return base64.b64decode(
                "".join(data["content"].split()), validate=True
            ).decode("utf-8")
        except (ValueError, UnicodeError):
            raise GitHubError("Invalid README encoding") from None
