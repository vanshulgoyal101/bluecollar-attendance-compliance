"""Auth + static-serving tests for server.py (Track C).

Reuses the fakes from test_api so no network or keys are needed.
"""

import pytest

from server import create_app
from test_api import FakeChatbot


def open_app():
    """App with auth explicitly disabled (deterministic, ignores env)."""
    app = create_app(chatbot=FakeChatbot())
    app.testing = True
    app.config["AUTH_TOKEN"] = ""
    app.config["AUTH_DEV_BYPASS"] = False
    return app


def auth_app(token="secret", dev_bypass=False):
    app = create_app(chatbot=FakeChatbot())
    app.testing = True
    app.config["AUTH_TOKEN"] = token
    app.config["AUTH_DEV_BYPASS"] = dev_bypass
    return app


# --- static / public pages ------------------------------------------------ #


def test_index_is_served():
    res = open_app().test_client().get("/")
    assert res.status_code == 200
    assert "Compliance & Operations Hub" in res.get_data(as_text=True)


def test_login_page_is_public():
    res = auth_app().test_client().get("/login")
    assert res.status_code == 200
    assert "Access token" in res.get_data(as_text=True)


# --- auth disabled (default / dev bypass) --------------------------------- #


def test_auth_disabled_allows_api():
    assert open_app().test_client().get("/api/employees").status_code == 200


def test_dev_bypass_opens_app_even_with_token():
    client = auth_app(dev_bypass=True).test_client()
    assert client.get("/api/employees").status_code == 200


# --- auth enabled --------------------------------------------------------- #


def test_api_blocked_without_credentials():
    res = auth_app().test_client().get("/api/employees")
    assert res.status_code == 401


def test_api_allows_bearer_token():
    res = auth_app().test_client().get(
        "/api/employees", headers={"Authorization": "Bearer secret"}
    )
    assert res.status_code == 200


def test_api_allows_x_auth_token_header():
    res = auth_app().test_client().get(
        "/api/employees", headers={"X-Auth-Token": "secret"}
    )
    assert res.status_code == 200


def test_health_stays_public_with_auth_enabled():
    res = auth_app().test_client().get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["auth_required"] is True


def test_html_request_redirects_to_login():
    res = auth_app().test_client().get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_session_login_logout_flow():
    client = auth_app().test_client()
    assert client.get("/api/employees").status_code == 401

    login = client.post("/api/login", json={"token": "secret"})
    assert login.status_code == 200
    assert client.get("/api/employees").status_code == 200

    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/employees").status_code == 401


def test_login_rejects_bad_token():
    res = auth_app().test_client().post("/api/login", json={"token": "wrong"})
    assert res.status_code == 401


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
