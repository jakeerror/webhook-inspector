import pytest


async def test_create_get_delete_bin(client, create_bin):
    bin_ = await create_bin()
    bid = bin_["id"]
    assert bin_["url"].endswith(f"/in/{bid}")

    got = await client.get(f"/api/v1/bins/{bid}")
    assert got.status_code == 200
    assert got.json()["id"] == bid

    assert (await client.delete(f"/api/v1/bins/{bid}")).status_code == 204
    assert (await client.get(f"/api/v1/bins/{bid}")).status_code == 404


async def test_ingest_captures_method_path_query_headers_body(client, create_bin):
    bid = (await create_bin())["id"]
    resp = await client.post(
        f"/in/{bid}/webhook/path?foo=bar&x=1",
        json={"hello": "world"},
        headers={"X-Custom": "abc"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    listing = (await client.get(f"/api/v1/bins/{bid}/requests")).json()
    assert len(listing) == 1
    assert listing[0]["method"] == "POST"
    assert listing[0]["path"] == "webhook/path"

    detail = (await client.get(f"/api/v1/bins/{bid}/requests/{listing[0]['id']}")).json()
    assert detail["query"] == {"foo": "bar", "x": "1"}
    assert detail["headers"]["x-custom"] == "abc"
    assert "world" in detail["body"]
    assert detail["source_ip"]  # populated


async def test_ingest_any_method(client, create_bin):
    bid = (await create_bin())["id"]
    for method in ("get", "put", "patch", "delete"):
        resp = await getattr(client, method)(f"/in/{bid}")
        assert resp.status_code == 200


async def test_ingest_unknown_bin_returns_404(client):
    resp = await client.post("/in/doesnotexist")
    assert resp.status_code == 404


async def test_body_truncated_at_limit(client, create_bin):
    bid = (await create_bin())["id"]
    big = "x" * 300_000  # exceeds default 256 KB
    await client.post(
        f"/in/{bid}",
        content=big.encode(),
        headers={"content-type": "text/plain"},
    )
    detail = (await client.get(f"/api/v1/bins/{bid}/requests")).json()[0]
    full = (await client.get(f"/api/v1/bins/{bid}/requests/{detail['id']}")).json()
    assert full["body_truncated"] is True
    assert full["size_bytes"] == 300_000
    assert len(full["body"]) == 262_144


async def test_ring_buffer_keeps_newest(client, create_bin):
    # conftest sets MAX_REQUESTS_PER_BIN=5
    bid = (await create_bin())["id"]
    for i in range(7):
        await client.post(f"/in/{bid}", json={"n": i})
    listing = (await client.get(f"/api/v1/bins/{bid}/requests?limit=100")).json()
    assert len(listing) == 5  # oldest two evicted
    got = await client.get(f"/api/v1/bins/{bid}")
    assert got.json()["request_count"] == 5


@pytest.mark.parametrize("target", ["http://169.254.169.254/", "http://localhost:9999/", "ftp://x/y"])
async def test_replay_blocked_by_ssrf(client, create_bin, target):
    bid = (await create_bin())["id"]
    await client.post(f"/in/{bid}", json={"a": 1})
    rid = (await client.get(f"/api/v1/bins/{bid}/requests")).json()[0]["id"]
    resp = await client.post(
        f"/api/v1/bins/{bid}/requests/{rid}/replay",
        json={"target_url": target},
    )
    assert resp.status_code == 403


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["db"] == "ok"
    assert body["redis"] == "disabled"
