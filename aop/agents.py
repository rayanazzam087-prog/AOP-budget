"""The four specialist agents used in AOP: code, math, search, commonsense."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

from . import prompts as P
from .ledger import Ledger
from .llm import LLM
from .search import Search

ANSWER_RE = re.compile(r"answer\s*[:：]\s*(.+)", re.I)
CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)


def extract_answer(text: str) -> str:
    m = list(ANSWER_RE.finditer(text))
    return m[-1].group(1).strip() if m else text.strip().splitlines()[-1][:300] if text.strip() else ""


def context_block(dep_results: dict[int, str]) -> str:
    if not dep_results:
        return ""
    lines = "\n".join(f"- Result of sub-task {k}: {v}" for k, v in dep_results.items())
    return f"\n\nResults of earlier sub-tasks you may need:\n{lines}"


class Agent:
    name = "agent"

    def __init__(self, llm: LLM):
        self.llm = llm

    @property
    def description(self) -> str:
        return P.AGENT_DESCRIPTIONS[self.name]

    def run(self, task: str, dep_results: dict[int, str], ledger: Ledger) -> dict:
        raise NotImplementedError

    def _simple(self, system: str, task: str, dep_results, ledger, stage: str) -> dict:
        user = P.AGENT_USER.format(task=task, context=context_block(dep_results))
        text = self.llm.chat([{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                             stage=stage, ledger=ledger, meta={"task": task, "agent": self.name})
        return {"answer": extract_answer(text), "response": text}


class MathAgent(Agent):
    name = "math_agent"

    def run(self, task, dep_results, ledger):
        return self._simple(P.MATH_SYSTEM, task, dep_results, ledger, "agent_math")


class CommonsenseAgent(Agent):
    name = "commonsense_agent"

    def run(self, task, dep_results, ledger):
        return self._simple(P.COMMONSENSE_SYSTEM, task, dep_results, ledger, "agent_commonsense")


class CodeAgent(Agent):
    """Generates Python and executes it in a subprocess with a timeout.

    WARNING: this runs model-written code on your machine. It runs in a temp dir with
    `python -I` and a timeout, which is NOT a security sandbox. Use a VM/container if
    you are worried."""
    name = "code_agent"

    def __init__(self, llm: LLM, timeout_s: int = 15):
        super().__init__(llm)
        self.timeout_s = timeout_s

    def run(self, task, dep_results, ledger):
        user = P.AGENT_USER.format(task=task, context=context_block(dep_results))
        text = self.llm.chat([{"role": "system", "content": P.CODE_SYSTEM},
                              {"role": "user", "content": user}],
                             stage="agent_code", ledger=ledger,
                             meta={"task": task, "agent": self.name})
        m = CODE_RE.search(text)
        code = m.group(1) if m else text
        ledger.add_tool("python")
        out = run_python(code, self.timeout_s)
        answer = out.strip().splitlines()[-1] if out.strip() else ""
        return {"answer": answer[:300], "response": f"Code:\n{code}\nOutput:\n{out[-1500:]}"}


def run_python(code: str, timeout_s: int) -> str:
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "main.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            r = subprocess.run([sys.executable, "-I", "-X", "utf8", path], cwd=d, capture_output=True,
                               encoding="utf-8", errors="replace", timeout=timeout_s)
            return r.stdout if r.returncode == 0 else f"[error]\n{r.stderr[-800:]}"
        except subprocess.TimeoutExpired:
            return "[error] timeout"


class SearchAgent(Agent):
    name = "search_agent"

    def __init__(self, llm: LLM, search: Search):
        super().__init__(llm)
        self.search = search

    def run(self, task, dep_results, ledger):
        ctx = context_block(dep_results)
        meta = {"task": task, "agent": self.name}
        q = self.llm.chat_json([{"role": "system", "content": P.SEARCH_QUERY_SYSTEM},
                                {"role": "user", "content": P.AGENT_USER.format(task=task, context=ctx)}],
                               stage="agent_search_query", ledger=ledger, meta=meta)
        query = str(q.get("query") or task)
        ledger.add_tool("search")
        results = self.search(query)
        user = P.AGENT_USER.format(task=task, context=ctx) + f"\n\nSearch query: {query}\nSearch results:\n{results}"
        text = self.llm.chat([{"role": "system", "content": P.SEARCH_ANSWER_SYSTEM},
                              {"role": "user", "content": user}],
                             stage="agent_search_answer", ledger=ledger, meta=meta)
        return {"answer": extract_answer(text), "response": text, "query": query}


def build_agents(llm: LLM, search: Search) -> dict[str, Agent]:
    agents = [CodeAgent(llm), MathAgent(llm), SearchAgent(llm, search), CommonsenseAgent(llm)]
    return {a.name: a for a in agents}
