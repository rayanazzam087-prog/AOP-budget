"""LLM client with cost tracking and a persistent response cache.

Providers
---------
* ``openai``  - any OpenAI-compatible endpoint: OpenAI, Groq, Together, OpenRouter,
                a local Ollama/vLLM server ... (set LLM_BASE_URL / LLM_API_KEY).
* ``anthropic`` - Claude models through the ``anthropic`` SDK.
* ``mock``    - deterministic fake model, no network, no key. Used for tests and for
                developing the pipeline before an API key is available.

The cache is what makes the experiment cheap and *paired*: every condition shares
the same initial plan, agent answers etc. whenever the prompt is identical, and
re-running a script costs nothing. Cached calls are still written to the ledger
with their original token counts and latency, so cost numbers stay honest.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .ledger import CallRecord, Ledger


@dataclass
class LLMConfig:
    provider: str = "mock"              # openai | anthropic | mock
    model: str = "gpt-4o-mini"
    base_url: str | None = None         # for OpenAI-compatible servers
    api_key: str | None = None
    temperature: float = 0.0
    max_tokens: int = 1024
    cache_path: str | None = ".cache/llm.sqlite"
    max_retries: int = 5
    seed: int | None = None             # extra cache-key salt for repeated runs

    @classmethod
    def from_env(cls, **overrides) -> "LLMConfig":
        cfg = cls(
            provider=os.getenv("LLM_PROVIDER", "mock"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("LLM_BASE_URL") or None,
            api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY") or None,
        )
        for k, v in overrides.items():
            if v is not None:
                setattr(cfg, k, v)
        return cfg


class _Cache:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS calls (key TEXT PRIMARY KEY, response TEXT,"
            " prompt_tokens INT, completion_tokens INT, latency REAL)")
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            row = self._conn.execute(
                "SELECT response, prompt_tokens, completion_tokens, latency FROM calls"
                " WHERE key=?", (key,)).fetchone()
        return row

    def put(self, key, response, pt, ct, latency):
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO calls VALUES (?,?,?,?,?)",
                               (key, response, pt, ct, latency))
            self._conn.commit()


class LLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.cache = _Cache(cfg.cache_path) if cfg.cache_path else None
        self._client = None
        if cfg.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
        elif cfg.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=cfg.api_key)
        elif cfg.provider == "mock":
            from .mock_llm import MockModel
            self._client = MockModel()
        else:
            raise ValueError(f"unknown provider {cfg.provider}")

    # ------------------------------------------------------------------
    def chat(self, messages: list[dict], *, stage: str, ledger: Ledger | None,
             json_mode: bool = False, max_tokens: int | None = None,
             meta: dict | None = None) -> str:
        """Send ``messages`` and return the text reply. ``stage`` labels the call
        in the cost ledger. ``meta`` is only read by the mock model."""
        max_tokens = max_tokens or self.cfg.max_tokens
        key = self._key(messages, json_mode, max_tokens)
        hit = self.cache.get(key) if self.cache else None
        if hit is not None:
            text, pt, ct, lat = hit
            cached = True
        else:
            t0 = time.time()
            text, pt, ct = self._call(messages, json_mode, max_tokens, stage, meta)
            lat = time.time() - t0
            cached = False
            if self.cache:
                self.cache.put(key, text, pt, ct, lat)
        if ledger is not None:
            ledger.add(CallRecord(stage, self.cfg.model, pt, ct, round(lat, 3), cached))
        return text

    def chat_json(self, messages, *, stage, ledger, max_tokens=None, meta=None) -> dict:
        """Like chat() but parses a JSON object out of the reply (one repair retry)."""
        text = self.chat(messages, stage=stage, ledger=ledger, json_mode=True,
                         max_tokens=max_tokens, meta=meta)
        try:
            return parse_json(text)
        except ValueError:
            repair = messages + [{"role": "assistant", "content": text},
                                 {"role": "user", "content": "That was not valid JSON. "
                                  "Reply again with ONLY the JSON object."}]
            text = self.chat(repair, stage=stage, ledger=ledger, json_mode=True,
                             max_tokens=max_tokens, meta=meta)
            return parse_json(text)

    # ------------------------------------------------------------------
    def _key(self, messages, json_mode, max_tokens) -> str:
        blob = json.dumps([self.cfg.provider, self.cfg.model, self.cfg.temperature,
                           max_tokens, json_mode, self.cfg.seed, messages],
                          sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _call(self, messages, json_mode, max_tokens, stage, meta):
        p = self.cfg.provider
        if p == "mock":
            text = self._client.respond(messages, stage=stage, meta=meta or {})
            pt = sum(len(m["content"]) for m in messages) // 4
            return text, pt, len(text) // 4
        last_err = None
        for attempt in range(self.cfg.max_retries):
            try:
                if p == "openai":
                    kw = dict(model=self.cfg.model, messages=messages,
                              temperature=self.cfg.temperature, max_tokens=max_tokens)
                    if json_mode:
                        kw["response_format"] = {"type": "json_object"}
                    r = self._client.chat.completions.create(**kw)
                    u = r.usage
                    return (r.choices[0].message.content or "",
                            getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
                if p == "anthropic":
                    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
                    rest = [m for m in messages if m["role"] != "system"]
                    kw = dict(model=self.cfg.model, messages=rest, max_tokens=max_tokens,
                              temperature=self.cfg.temperature)
                    if system:
                        kw["system"] = system
                    r = self._client.messages.create(**kw)
                    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
                    return text, r.usage.input_tokens, r.usage.output_tokens
            except Exception as e:  # rate limits, timeouts ... back off and retry
                last_err = e
                time.sleep(min(60, 2 ** attempt))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")


_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_RE.search(text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise ValueError(f"could not parse JSON from: {text[:200]}")
