"""Search backends for the search agent, with an on-disk cache.

AOP used the Bing Search API, which Microsoft retired on 11 Aug 2025, so we offer:
  * wikipedia - free, no key (default). Good for HuskyQA-style factual questions.
  * tavily    - needs TAVILY_API_KEY (free tier available).
  * serper    - Google results, needs SERPER_API_KEY (free tier available).
  * mock      - offline fake results for tests.
Every result is cached, so re-runs and all experimental conditions see identical evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Wikimedia asks for a descriptive User-Agent with contact info; set SEARCH_CONTACT in .env.
def _ua() -> dict:  # read at call time, after .env is loaded
    return {"User-Agent": f"AOP-Budget/0.2 (university course project; "
                          f"{os.getenv('SEARCH_CONTACT', 'contact via GitHub')}) python-urllib"}


class _RateLimiter:
    """At most one request every ``interval`` seconds, across all threads."""

    def __init__(self, interval: float):
        self.interval, self._next, self._lock = interval, 0.0, threading.Lock()

    def wait(self):
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.interval
        if delay:
            time.sleep(delay)


_LIMIT = _RateLimiter(float(os.getenv("SEARCH_MIN_INTERVAL", "0.5")))


def _request(req: urllib.request.Request, timeout: float, retries: int = 5) -> dict:
    """GET/POST with a global rate limit and exponential back-off on 429 / 5xx / network errors."""
    last = None
    for attempt in range(retries):
        _LIMIT.wait()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
            retry_after = e.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last, wait = e, 2 ** attempt
        time.sleep(min(30.0, wait))
    raise RuntimeError(f"failed after {retries} attempts: {last}")


def _get(url: str, timeout=20) -> dict:
    return _request(urllib.request.Request(url, headers=_ua()), timeout)


def _post(url: str, payload: dict, headers: dict, timeout=30) -> dict:
    return _request(urllib.request.Request(url, data=json.dumps(payload).encode(),
                                           headers={**_ua(), "Content-Type": "application/json", **headers}),
                    timeout)


class Search:
    def __init__(self, backend: str = "wikipedia", top_k: int = 3,
                 cache_path: str | None = ".cache/search.sqlite"):
        self.backend, self.top_k = backend, top_k
        self._lock = threading.Lock()
        self.stats = {"ok": 0, "cached": 0, "error": 0}
        self.last_error = None
        self._db = None
        if cache_path:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(cache_path, check_same_thread=False)
            self._db.execute("CREATE TABLE IF NOT EXISTS s (key TEXT PRIMARY KEY, val TEXT)")

    def __call__(self, query: str) -> str:
        key = hashlib.sha256(f"{self.backend}|{self.top_k}|{query}".encode()).hexdigest()
        if self._db:
            with self._lock:
                row = self._db.execute("SELECT val FROM s WHERE key=?", (key,)).fetchone()
            if row:
                self.stats["cached"] += 1
                return row[0]
        try:
            text = getattr(self, f"_{self.backend}")(query)
            self.stats["ok"] += 1
        except Exception as e:  # network errors are returned to the agent, not raised (or cached)
            self.stats["error"] += 1
            self.last_error = repr(e)
            if self.stats["error"] in (1, 10, 100) or self.stats["error"] % 500 == 0:
                print(f"[search] error #{self.stats['error']}: {e!r}")
            return f"[search error: {e}]"
        if self._db:
            with self._lock:
                self._db.execute("INSERT OR REPLACE INTO s VALUES (?,?)", (key, text))
                self._db.commit()
        return text

    # ------------------------------------------------------------------
    def _wikipedia(self, query: str) -> str:
        # one request: search + intro extracts of the top hits
        api = "https://en.wikipedia.org/w/api.php?"
        r = _get(api + urllib.parse.urlencode({
            "action": "query", "generator": "search", "gsrsearch": query, "gsrlimit": self.top_k,
            "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": self.top_k,
            "format": "json", "formatversion": 2}))
        pages = sorted((r.get("query") or {}).get("pages", []), key=lambda p: p.get("index", 0))
        if not pages:
            return "No results."
        return "\n\n".join(f"## {p.get('title')}\n{(p.get('extract') or '')[:1500]}" for p in pages)

    def _tavily(self, query: str) -> str:
        r = _post("https://api.tavily.com/search",
                  {"query": query, "max_results": self.top_k, "include_answer": True},
                  {"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"})
        parts = [f"Answer box: {r['answer']}"] if r.get("answer") else []
        parts += [f"## {x['title']}\n{x['content'][:1200]}" for x in r.get("results", [])]
        return "\n\n".join(parts) or "No results."

    def _serper(self, query: str) -> str:
        r = _post("https://google.serper.dev/search", {"q": query, "num": self.top_k},
                  {"X-API-KEY": os.environ["SERPER_API_KEY"]})
        parts = []
        if "answerBox" in r:
            ab = r["answerBox"]
            parts.append(f"Answer box: {ab.get('answer') or ab.get('snippet', '')}")
        parts += [f"## {x.get('title')}\n{x.get('snippet', '')}" for x in r.get("organic", [])[: self.top_k]]
        return "\n\n".join(parts) or "No results."

    def _mock(self, query: str) -> str:
        return f"## Mock result\nA made-up snippet about '{query}'. The figure is 42."
