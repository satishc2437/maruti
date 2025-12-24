"""Runtime initialization coverage for tools.

This covers `initialize_runtime_from_env()` caching behavior without requiring a real
GitHub App private key to be parsed (we monkeypatch auth/client classes).
"""

from __future__ import annotations

from pathlib import Path

import github_app_mcp.tools as tools
import pytest


def test_initialize_runtime_from_env_caches_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))

    class DummyAuth:
        def __init__(self, *, config, _transport=None) -> None:  # noqa: ANN001
            self.config = config

        async def get_installation_token(self) -> str:
            return "tok"

    class DummyGitHub:
        def __init__(
            self,
            *,
            token_provider,
            limits,
            _api_base_url="https://api.github.com",
            _transport=None,
        ) -> None:  # noqa: ANN001
            self.token_provider = token_provider
            self.limits = limits

    class DummyGraphQL:
        def __init__(
            self,
            *,
            token_provider,
            limits,
            _api_base_url="https://api.github.com",
            _transport=None,
        ) -> None:  # noqa: ANN001
            self.token_provider = token_provider
            self.limits = limits

    monkeypatch.setattr(tools, "GitHubAppAuth", DummyAuth)
    monkeypatch.setattr(tools, "GitHubClient", DummyGitHub)
    monkeypatch.setattr(tools, "GitHubGraphQLClient", DummyGraphQL)
    monkeypatch.setattr(tools, "_RUNTIME", None)

    r1 = tools.initialize_runtime_from_env()
    r2 = tools.initialize_runtime_from_env()

    assert r1 is r2
    assert r1.config.app_id == 1
