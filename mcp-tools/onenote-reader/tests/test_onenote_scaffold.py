import asyncio
import sys
import types

import pytest
from onenote_reader import auth, config, errors, graph_client, safety, tools


def test_validate_share_link_accepts_known_patterns():
    safety.validate_share_link("https://1drv.ms/u/s!abcdef")
    safety.validate_share_link("https://contoso.onenote.com/some/path")
    safety.validate_share_link("https://contoso.onenote.officeapps.live.com/some/path")


def test_validate_share_link_rejects_invalid():
    with pytest.raises(ValueError):
        safety.validate_share_link("")
    with pytest.raises(ValueError):
        safety.validate_share_link("not-a-link")
    with pytest.raises(ValueError):
        safety.validate_share_link(123)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        safety.validate_share_link("https://1drv.ms/" + ("a" * 5000))


def test_rate_limit_enforced_and_resets(monkeypatch):
    # Reset module global state deterministically.
    safety._rate_window = (0.0, 0)  # type: ignore[attr-defined]

    t = {"now": 100.0}

    def fake_time():
        return t["now"]

    monkeypatch.setattr(safety.time, "time", fake_time)

    # Allow up to RATE_LIMIT_MAX_CALLS within window.
    for _ in range(config.RATE_LIMIT_MAX_CALLS):
        assert safety.check_rate_limit() is None

    err = safety.check_rate_limit()
    assert err is not None
    assert err["ok"] is False

    # Advance time beyond window to reset.
    t["now"] = 100.0 + config.RATE_LIMIT_WINDOW_SECONDS + 0.1
    assert safety.check_rate_limit() is None


def test_auth_token_cache_roundtrip():
    auth.clear_token()
    assert auth.get_cached_token() is None

    token_info = auth.ensure_token()
    assert token_info["ok"] is True

    cached = auth.get_cached_token()
    assert cached is not None
    assert "access_token" in cached


def test_auth_ensure_token_internal_error(monkeypatch):
    auth.clear_token()

    def boom():
        raise RuntimeError("fail")

    monkeypatch.setattr(auth, "_now", boom)
    resp = auth.ensure_token()
    assert resp["ok"] is False
    assert resp["code"] == "Internal"


def test_auth_status_snapshot():
    auth.clear_token()
    status = auth.auth_status()
    assert status["has_token"] is False

    auth.ensure_token()
    status = auth.auth_status()
    assert status["has_token"] is True


def test_graph_client_token_failure_paths(monkeypatch):
    monkeypatch.setattr(graph_client, "check_rate_limit", lambda: None)
    monkeypatch.setattr(
        graph_client,
        "ensure_token",
        lambda *args, **kwargs: {"ok": False, "code": "Internal", "message": "no token"},
    )

    share = "https://1drv.ms/u/s!abcdef"
    assert graph_client.resolve_share_link(share)["ok"] is False
    assert graph_client.read_page(share, "plain", False, None)["ok"] is False
    assert graph_client.write_page(share, "append", "<p>x</p>", None, "bottom")["ok"] is False
    assert graph_client.list_page_children(share, "all")["ok"] is False
    assert graph_client.traverse_notebook(share, "summary", 2000)["ok"] is False


def test_errors_helpers_cover_branches():
    assert errors.user_input_error("m")["code"] == "UserInput"
    assert errors.forbidden_error("m")["code"] == "Forbidden"
    assert errors.not_found_error("m")["code"] == "NotFound"
    assert errors.timeout_error("m")["code"] == "Timeout"

    internal = errors.internal_error("oops", detail="x" * 1000)
    assert internal["code"] == "Internal"
    assert len(internal.get("detail", "")) <= 403

    # ensure_error pass-through and wrapper
    passthrough = {"ok": False, "code": "UserInput", "message": "x"}
    assert errors.ensure_error(passthrough) is passthrough
    wrapped = errors.ensure_error("boom")
    assert wrapped["ok"] is False
    assert wrapped["code"] == "Internal"


def test_safety_misc_helpers():
    assert safety.validate_content_html("<p>x</p>") is None
    assert safety.validate_content_html("   ")["ok"] is False
    assert safety.validate_content_html(123)["ok"] is False  # type: ignore[arg-type]

    assert safety.truncate_plaintext("abcd", max_chars=3) == "..."
    assert safety.truncate_plaintext(123, max_chars=2) == ""

    # sanitize_html: cover both real-import and fallback branches.
    fake = types.SimpleNamespace(sanitize_html=lambda html: "SANITIZED:" + html)
    sys.modules["onenote_reader.html_sanitizer"] = fake  # type: ignore[assignment]
    assert safety.sanitize_html("<p>x</p>") == "SANITIZED:<p>x</p>"
    sys.modules.pop("onenote_reader.html_sanitizer", None)
    assert safety.sanitize_html("<p>x</p>") == "<p>x</p>"

    status = safety.safety_status()
    assert status["phase"] == "scaffold"


def test_config_is_valid_share_link_covers_negative_cases():
    assert config.is_valid_share_link("https://1drv.ms/u/s!abcdef") is True
    assert config.is_valid_share_link("x") is False
    assert config.is_valid_share_link("https://1drv.ms/" + ("a" * 5000)) is False


def test_graph_client_scaffold_happy_paths(monkeypatch):
    auth.clear_token()

    # Avoid flakiness from global rate limiting across the suite.
    monkeypatch.setattr(graph_client, "check_rate_limit", lambda: None)

    share = "https://1drv.ms/u/s!abcdef"
    resolved = graph_client.resolve_share_link(share)
    assert resolved["ok"] is True
    assert resolved["data"]["type"] in ("page", "section")

    # Heuristic section branch
    resolved_section = graph_client.resolve_share_link("https://1drv.ms/section/abc")
    assert resolved_section["ok"] is True
    assert resolved_section["data"]["type"] == "section"

    read_plain = graph_client.read_page(share, "plain", include_images=False, max_chars=10)
    assert read_plain["ok"] is True
    assert read_plain["data"]["format"] == "plain"
    assert read_plain["data"]["plain_text"].endswith("...") or len(read_plain["data"]["plain_text"]) <= 10

    read_html = graph_client.read_page(share, "html", include_images=True, max_chars=None)
    assert read_html["ok"] is True
    assert "html" in read_html["data"]
    assert "images" in read_html["data"]

    read_json = graph_client.read_page(share, "json", include_images=False, max_chars=None)
    assert read_json["ok"] is True
    assert "json" in read_json["data"]

    children = graph_client.list_page_children(share, "all")
    assert children["ok"] is True
    assert isinstance(children["data"]["elements"], list)

    write = graph_client.write_page(share, "append", "<p>Hello</p>", title=None, position="bottom")
    assert write["ok"] is True
    assert write["data"]["fragment_length"] == len("<p>Hello</p>")

    tree = graph_client.traverse_notebook(share, "summary", 2000)
    assert tree["ok"] is True
    assert "sections" in tree["data"]


def test_graph_client_rejects_bad_inputs():
    err = graph_client.read_page("not-a-link", "plain", False, None)
    assert err["ok"] is False

    err = graph_client.read_page("https://1drv.ms/u/s!abcdef", "badfmt", False, None)
    assert err["ok"] is False

    err = graph_client.write_page("https://1drv.ms/u/s!abcdef", "badmode", "<p>x</p>", None, "bottom")
    assert err["ok"] is False

    err = graph_client.list_page_children("https://1drv.ms/u/s!abcdef", "badtype")
    assert err["ok"] is False

    # Too-long share link triggers validation error path.
    long_link = "https://1drv.ms/" + ("a" * 5000)
    err = graph_client.resolve_share_link(long_link)
    assert err["ok"] is False


def test_tools_dispatch_smoke():
    share = "https://1drv.ms/u/s!abcdef"

    # Reset limiter state for this test.
    safety._rate_window = (0.0, 0)  # type: ignore[attr-defined]

    read = asyncio.run(tools.tool_read_onenote_page({"share_link": share, "format": "plain"}))
    assert read["ok"] is True

    write = asyncio.run(
        tools.tool_write_onenote_page(
            {"share_link": share, "mode": "append", "content_html": "<p>x</p>", "position": "top"}
        )
    )
    assert write["ok"] is True

    children = asyncio.run(tools.tool_list_onenote_page_children({"share_link": share, "type": "images"}))
    assert children["ok"] is True

    safety._rate_window = (0.0, 0)  # type: ignore[attr-defined]
    tree = asyncio.run(
        tools.tool_traverse_onenote_notebook(
            {"share_link": share, "content_mode": "plain", "max_chars_per_page": 150}
        )
    )
    assert tree["ok"] is True

    assert set(tools.TOOL_DISPATCH.keys()) == {
        "read_onenote_page",
        "write_onenote_page",
        "list_onenote_page_children",
        "traverse_onenote_notebook",
    }


def test_tools_reject_bad_params():
    share = "https://1drv.ms/u/s!abcdef"
    safety._rate_window = (0.0, 0)  # type: ignore[attr-defined]

    # Bad max_chars type
    r = asyncio.run(tools.tool_read_onenote_page({"share_link": share, "max_chars": "nope"}))
    assert r["ok"] is False

    # Missing share_link
    r = asyncio.run(tools.tool_read_onenote_page({}))
    assert r["ok"] is False

    # share_link that fails validate_share_link (covers _require_share_link re-raise)
    r = asyncio.run(tools.tool_read_onenote_page({"share_link": "not-a-link"}))
    assert r["ok"] is False

    # Too-long share_link
    r = asyncio.run(tools.tool_read_onenote_page({"share_link": "https://1drv.ms/" + ("a" * 5000)}))
    assert r["ok"] is False

    # Bad mode
    r = asyncio.run(tools.tool_write_onenote_page({"share_link": share, "mode": "nope", "content_html": "<p>x</p>"}))
    assert r["ok"] is False

    # share_link invalid
    r = asyncio.run(tools.tool_write_onenote_page({"share_link": "not-a-link", "content_html": "<p>x</p>"}))
    assert r["ok"] is False

    # Bad position
    r = asyncio.run(
        tools.tool_write_onenote_page(
            {"share_link": share, "mode": "append", "position": "nope", "content_html": "<p>x</p>"}
        )
    )
    assert r["ok"] is False

    # Bad title type
    r = asyncio.run(
        tools.tool_write_onenote_page(
            {"share_link": share, "mode": "append", "position": "bottom", "content_html": "<p>x</p>", "title": 123}
        )
    )
    assert r["ok"] is False

    # Missing content_html
    r = asyncio.run(tools.tool_write_onenote_page({"share_link": share}))
    assert r["ok"] is False

    # Too-large HTML (hits validate_content_html length branch)
    big_html = "<p>" + ("a" * (config.MAX_CONTENT_HTML_CHARS + 1)) + "</p>"
    r = asyncio.run(
        tools.tool_write_onenote_page(
            {"share_link": share, "mode": "append", "position": "bottom", "content_html": big_html}
        )
    )
    assert r["ok"] is False

    # Bad children type
    r = asyncio.run(tools.tool_list_onenote_page_children({"share_link": share, "type": "nope"}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_list_onenote_page_children({"share_link": "not-a-link", "type": "all"}))
    assert r["ok"] is False

    # Bad traverse params
    r = asyncio.run(tools.tool_traverse_onenote_notebook({"share_link": share, "content_mode": "nope"}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_traverse_onenote_notebook({"share_link": share, "max_chars_per_page": 10}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_traverse_onenote_notebook({"share_link": share, "max_chars_per_page": "nope"}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_traverse_onenote_notebook({"share_link": "not-a-link"}))
    assert r["ok"] is False


def test_graph_client_rate_limit_error_path(monkeypatch):
    # Force rate limit to be exceeded.
    safety._rate_window = (0.0, config.RATE_LIMIT_MAX_CALLS)  # type: ignore[attr-defined]

    t = {"now": 0.0}

    def fake_time():
        return t["now"]

    monkeypatch.setattr(safety.time, "time", fake_time)

    err = graph_client.read_page("https://1drv.ms/u/s!abcdef", "plain", False, None)
    assert err["ok"] is False


def test_graph_client_children_filters_and_traversal_modes(monkeypatch):
    monkeypatch.setattr(graph_client, "check_rate_limit", lambda: None)

    share = "https://1drv.ms/u/s!abcdef"
    imgs = graph_client.list_page_children(share, "images")
    assert imgs["ok"] is True

    outlines = graph_client.list_page_children(share, "outlines")
    assert outlines["ok"] is True

    plain = graph_client.traverse_notebook(share, "plain", 120)
    assert plain["ok"] is True

    html = graph_client.traverse_notebook(share, "html", 120)
    assert html["ok"] is True


def test_graph_client_rate_limit_helper_passthrough(monkeypatch):
    # Make the helper return an error dict and ensure public functions pass it through.
    err = errors.user_input_error("Rate limit exceeded", hint="retry")
    monkeypatch.setattr(graph_client, "check_rate_limit", lambda: err)

    share = "https://1drv.ms/u/s!abcdef"
    out = graph_client.resolve_share_link(share)
    assert out is err


def test_package_entrypoint_main_prints(capsys):
    from onenote_reader import main

    main()
    out = capsys.readouterr().out
    assert "onenote-reader" in out
