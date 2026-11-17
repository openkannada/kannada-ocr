import json

import pytest

from kannada_ocr.http import Client, Disallowed

ROBOTS = "User-agent: *\nDisallow: /w/\nAllow: /wiki/\n"


class Fake(Client):
    def __init__(self, tmp_path, responses):
        super().__init__(tmp_path / "cache", tmp_path / "log.jsonl", interval=0)
        self.responses = responses
        self.calls = []

    def _fetch(self, url):
        self.calls.append(url)
        return self.responses[url]


def test_robots_rules_are_obeyed(tmp_path):
    c = Fake(tmp_path, {"https://x.org/robots.txt": ROBOTS.encode(), "https://x.org/wiki/A": b"a"})
    assert c.get("https://x.org/wiki/A") == b"a"
    with pytest.raises(Disallowed):
        c.get("https://x.org/w/api.php?action=query")


def test_responses_are_cached(tmp_path):
    c = Fake(tmp_path, {"https://x.org/robots.txt": b"", "https://x.org/p": b"body"})
    c.get("https://x.org/p")
    c.get("https://x.org/p")
    assert c.calls.count("https://x.org/p") == 1


def test_an_html_robots_page_has_no_rules(tmp_path):
    parked = b"<html><head></head><body>parked</body></html>"
    c = Fake(tmp_path, {"http://y.in/robots.txt": parked, "http://y.in/w/f.zip": b"zip"})
    assert c.get("http://y.in/w/f.zip") == b"zip"


def test_log_lines_are_json(tmp_path):
    c = Client(tmp_path / "cache", tmp_path / "log.jsonl")
    c._log("https://x.org/", 200, 5)
    entry = json.loads((tmp_path / "log.jsonl").read_text())
    assert entry["status"] == 200 and entry["bytes"] == 5


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_requests_wait_between_calls_and_retry_on_429(tmp_path, monkeypatch):
    import email.message
    import urllib.error

    import kannada_ocr.http as http

    clock = {"now": 100.0}
    sleeps = []
    monkeypatch.setattr(http.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(http.time, "sleep", lambda s: sleeps.append(s))
    headers = email.message.Message()
    headers["Retry-After"] = "7"
    replies = [
        urllib.error.HTTPError("https://x.org/a", 429, "slow down", headers, None),
        Response(b"a"),
        Response(b"b"),
    ]

    def urlopen(request, timeout):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(http.urllib.request, "urlopen", urlopen)
    c = Client(tmp_path / "cache", tmp_path / "log.jsonl", interval=1.0)
    assert c._fetch("https://x.org/a") == b"a"
    assert c._fetch("https://x.org/b") == b"b"
    assert sleeps == [7.0, 1.0, 1.0]
    statuses = [
        json.loads(line)["status"] for line in (tmp_path / "log.jsonl").read_text().splitlines()
    ]
    assert statuses == [429, 200, 200]


def test_the_user_agent_says_where_to_find_the_project():
    from kannada_ocr.http import USER_AGENT

    assert "https://github.com/openkannada/kannada-ocr" in USER_AGENT
