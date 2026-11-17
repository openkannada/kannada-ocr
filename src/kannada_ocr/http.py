"""A slow, cached HTTP client that obeys robots.txt and logs every request."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

USER_AGENT = (
    "kannada-ocr/0.1 (+https://github.com/openkannada/kannada-ocr; about 1 request per second)"
)


class Disallowed(Exception):
    """robots.txt does not allow this URL for our user agent."""


@dataclass
class Client:
    """Fetches URLs at most once per `interval` seconds per host.

    Responses are cached under `cache_dir`, so a rerun makes no new requests.
    Every network request is appended to `log_path` as 1 JSON line.
    """

    cache_dir: Path
    log_path: Path
    interval: float = 1.0
    user_agent: str = USER_AGENT
    _last: dict[str, float] = field(default_factory=dict)
    _robots: dict[str, urllib.robotparser.RobotFileParser | None] = field(default_factory=dict)

    def get(self, url: str) -> bytes:
        path = self.cache_dir / hashlib.sha256(url.encode()).hexdigest()
        if path.exists():
            return path.read_bytes()
        if not self.allowed(url):
            raise Disallowed(url)
        body = self._fetch(url)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return body

    def download(self, url: str, dest: Path) -> Path:
        """Saves a large file to `dest` once, without a second copy in the cache."""
        if dest.exists():
            return dest
        if not self.allowed(url):
            raise Disallowed(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_suffix(dest.suffix + ".part")
        partial.write_bytes(self._fetch(url))
        partial.rename(dest)
        return dest

    def get_text(self, url: str) -> str:
        return self.get(url).decode("utf-8")

    def allowed(self, url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        robots = self._robots[origin]
        return robots is None or robots.can_fetch(self.user_agent, url)

    def _load_robots(self, origin: str) -> urllib.robotparser.RobotFileParser | None:
        try:
            text = self._fetch(origin + "/robots.txt").decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None
            raise
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(text.splitlines())
        return parser

    def _fetch(self, url: str) -> bytes:
        host = urllib.parse.urlsplit(url).netloc
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        for attempt in range(5):
            wait = self._last.get(host, 0.0) + self.interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = response.read()
                    self._log(url, response.status, len(body))
                    return body
            except urllib.error.HTTPError as e:
                self._log(url, e.code, 0)
                if e.code not in (429, 503) or attempt == 4:
                    raise
                retry = e.headers.get("Retry-After")
                time.sleep(float(retry) if retry and retry.isdigit() else 10.0 * 2**attempt)
            finally:
                self._last[host] = time.monotonic()
        raise AssertionError("unreachable")

    def _log(self, url: str, status: int, size: int) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "url": url,
            "status": status,
            "bytes": size,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
