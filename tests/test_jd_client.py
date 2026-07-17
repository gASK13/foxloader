from app.config import JdLocalConfig
from app.services.jd_client import JdClientError, LocalJdClient


class FakeResponse:
    def __init__(self, status_code: int = 200, json_data=None, text: str = "", content: bytes = b"x") -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.content = content

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, json=None, timeout: int = 15):
        self.calls.append({"method": method, "url": url, "json": json, "timeout": timeout})
        return self.responses.pop(0)


def make_config() -> JdLocalConfig:
    return JdLocalConfig(
        base_url="http://127.0.0.1:3129",
        request_timeout_seconds=15,
    )


def test_add_links_posts_to_local_linkgrabber_endpoint() -> None:
    session = FakeSession([FakeResponse(json_data={"ok": True})])
    client = LocalJdClient(make_config(), session=session)  # type: ignore[arg-type]

    client.add_links(["https://example.com/file1"], "/downloads/incoming", package_name="incoming")

    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["json"] is None
    assert session.calls[0]["url"].startswith("http://127.0.0.1:3129/linkgrabberv2/addLinks?")
    assert "destinationFolder" in session.calls[0]["url"]
    assert "overwritePackagizerRules" in session.calls[0]["url"]
    assert "assignJobID" in session.calls[0]["url"]


def test_add_links_falls_back_to_legacy_linkcollector_endpoint() -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=500, text="internal error"),
            FakeResponse(json_data=True),
        ]
    )
    client = LocalJdClient(make_config(), session=session)  # type: ignore[arg-type]

    client.add_links(["https://example.com/file1"], "/downloads/incoming", package_name="incoming")

    assert len(session.calls) == 2
    assert session.calls[0]["url"].startswith("http://127.0.0.1:3129/linkgrabberv2/addLinks?")
    assert session.calls[1]["url"].startswith("http://127.0.0.1:3129/linkcollector/addLinks?")
    assert "%2Fdownloads%2Fincoming" in session.calls[1]["url"]


def test_fetch_queue_items_maps_progress() -> None:
    session = FakeSession(
        [
            FakeResponse(
                json_data={
                    "data": [
                        {
                            "uuid": 123,
                            "name": "Example File",
                            "status": "RUNNING",
                            "bytesTotal": 200,
                            "bytesLoaded": 50,
                            "speed": 1024,
                            "saveTo": "/downloads/incoming",
                            "packageName": "incoming",
                            "eta": 30,
                        }
                    ]
                }
            )
        ]
    )
    client = LocalJdClient(make_config(), session=session)  # type: ignore[arg-type]

    items = client.fetch_queue_items()

    assert len(items) == 1
    assert items[0].id == "123"
    assert items[0].progress_percent == 25.0
    assert items[0].target_path == "/downloads/incoming"
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"].startswith("http://127.0.0.1:3129/downloadsV2/queryLinks?")


def test_http_error_raises_jd_client_error() -> None:
    session = FakeSession([FakeResponse(status_code=500, text="boom")])
    client = LocalJdClient(make_config(), session=session)  # type: ignore[arg-type]

    try:
        client.fetch_queue_items()
    except JdClientError as exc:
        assert "HTTP 500" in str(exc)
        assert "boom" in str(exc)
    else:
        raise AssertionError("Expected JdClientError")
