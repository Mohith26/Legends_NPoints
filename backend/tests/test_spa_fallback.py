import pytest

# The SPA fallback only exists when the React build is present; it is
# tracked in git so it is available locally and in CI.
SPA_ROUTES = ["/labels", "/labels/1", "/topic/1", "/methodology"]


@pytest.mark.parametrize("path", SPA_ROUTES)
def test_client_side_routes_serve_index_html(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<div id="root"></div>' in response.text


def test_root_still_serves_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.parametrize("path", ["/assets/nope.js", "/vite.svg", "/labels/1.json"])
def test_missing_file_with_extension_returns_404(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert not response.headers["content-type"].startswith("text/html")


def test_api_topics_still_works(client):
    response = client.get("/api/topics")
    assert response.status_code == 200
    assert response.json()["topics"] == []
