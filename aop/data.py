"""Dataset loading. Every dataset is a JSONL file with at least "question" and "answer".

HuskyQA / DROP* / IIRC* (the AOP benchmarks) are distributed by the HUSKY authors on
HuggingFace; scripts/download_data.py converts them to data/<name>/<split>.jsonl.
"""
from __future__ import annotations

import json
import random
from pathlib import Path


def load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            r.setdefault("id", str(r.get("index", r.get("qid", i))))
            r["id"] = str(r["id"])
            if "question" not in r:
                r["question"] = r.get("query") or r.get("input")
            if "answer" not in r:
                r["answer"] = r.get("gold") or r.get("answers") or r.get("output")
            rows.append(r)
    return rows


def load_split(dataset: str, split: str, data_dir: str = "data", limit: int | None = None,
               seed: int = 0) -> list[dict]:
    rows = load_jsonl(Path(data_dir) / dataset / f"{split}.jsonl")
    if limit and limit < len(rows):
        rows = random.Random(seed).sample(rows, limit)   # fixed random subset
        rows.sort(key=lambda r: r["id"])
    return rows
