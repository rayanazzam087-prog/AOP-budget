"""Answer checking: rule-based exact/numeric match + LLM judge (as AOP used GPT-4o)."""
from __future__ import annotations

import re
import string

from . import prompts as P
from .ledger import Ledger
from .llm import LLM

_NUM = re.compile(r"-?\d[\d,]*\.?\d*(?:e-?\d+)?")


def normalize_text(s: str) -> str:
    s = str(s).lower().strip()
    s = "".join(ch for ch in s if ch not in set(string.punctuation) - {"."})
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split()).rstrip(".")


def _numbers(s: str) -> list[float]:
    out = []
    for m in _NUM.findall(str(s)):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def exact_match(pred: str, gold) -> bool:
    golds = gold if isinstance(gold, list) else [gold]
    return any(normalize_text(pred) == normalize_text(g) for g in golds)


def numeric_match(pred: str, gold, rel_tol: float = 0.01) -> bool | None:
    """None if gold is not numeric. Otherwise True if the first number in ``pred``
    matches gold within 1% (HuskyQA answers are mostly numbers)."""
    golds = gold if isinstance(gold, list) else [gold]
    gnums = [n for g in golds for n in _numbers(g)]
    if not gnums or len(normalize_text(golds[0]).split()) > 3:
        return None
    pnums = _numbers(pred)
    if not pnums:
        return False
    return any(abs(p - g) <= rel_tol * max(1.0, abs(g)) for p in pnums[:1] for g in gnums)


def llm_judge(llm: LLM, question: str, gold, pred: str, ledger: Ledger | None = None) -> bool:
    gold_s = " | ".join(map(str, gold)) if isinstance(gold, list) else str(gold)
    out = llm.chat_json([{"role": "system", "content": P.JUDGE_SYSTEM},
                         {"role": "user", "content": P.JUDGE_USER.format(question=question, gold=gold_s, pred=pred)}],
                        stage="judge", ledger=ledger,
                        meta={"question": question, "gold": gold_s, "pred": pred})
    return bool(out.get("correct"))


def grade(question: str, gold, pred: str, judge_llm: LLM | None) -> dict:
    em = exact_match(pred, gold)
    num = numeric_match(pred, gold)
    judge = None
    if judge_llm is not None:
        try:
            judge = llm_judge(judge_llm, question, gold, pred)
        except Exception as e:  # keep going; judge can be re-run later
            judge = None
            print(f"[judge] failed: {e}")
    correct = judge if judge is not None else (num if num is not None else em)
    return {"em": em, "numeric": num, "judge": judge, "correct": bool(correct)}
