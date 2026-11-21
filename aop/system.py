"""Builds the whole system from command-line args + environment (.env)."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .agents import build_agents
from .llm import LLM, LLMConfig
from .reward_model import RewardModel, RepresentativeWorks, make_embedder
from .search import Search


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines), so python-dotenv is not required."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def add_common_args(ap: argparse.ArgumentParser) -> None:
    g = ap.add_argument_group("system")
    g.add_argument("--provider", default=None, help="openai | anthropic | mock (default: $LLM_PROVIDER or mock)")
    g.add_argument("--model", default=None, help="model for meta-agent + agents (default: $LLM_MODEL)")
    g.add_argument("--judge-model", default=None, help="model for the answer judge / scorer (default: $JUDGE_MODEL or --model)")
    g.add_argument("--search", default=None, help="wikipedia | tavily | serper | mock (default: $SEARCH_BACKEND or wikipedia)")
    g.add_argument("--embedder", default="auto", help="auto | minilm | hash")
    g.add_argument("--reward-model", default="models/reward_model.npz")
    g.add_argument("--rep-works", default="models/rep_works.json")
    g.add_argument("--cache-dir", default=".cache")
    g.add_argument("--seed", type=int, default=None, help="cache salt: use different seeds for repeated runs")
    g.add_argument("--data-dir", default="data")


def pick_embedder(args, provider: str):
    """MiniLM (as in the paper) for real runs; hashing embedder for the mock pipeline."""
    kind = "hash" if provider == "mock" and args.embedder == "auto" else args.embedder
    return make_embedder(kind)


def build(args, need_rm: bool = True):
    load_dotenv()
    llm_cfg = LLMConfig.from_env(provider=args.provider, model=args.model, seed=args.seed,
                                 cache_path=f"{args.cache_dir}/llm.sqlite")
    llm = LLM(llm_cfg)
    judge_model = args.judge_model or os.getenv("JUDGE_MODEL") or llm_cfg.model
    judge_llm = LLM(LLMConfig.from_env(provider=args.provider, model=judge_model,
                                       cache_path=f"{args.cache_dir}/llm.sqlite"))
    backend = args.search or os.getenv("SEARCH_BACKEND") or ("mock" if llm_cfg.provider == "mock" else "wikipedia")
    search = Search(backend, cache_path=f"{args.cache_dir}/search.sqlite")
    agents = build_agents(llm, search)
    rm = rw = None
    if need_rm:
        emb = pick_embedder(args, llm_cfg.provider)
        if Path(args.reward_model + ".json").exists():
            rm = RewardModel.load(args.reward_model, emb)
        if Path(args.rep_works).exists():
            rw = RepresentativeWorks.load(args.rep_works, emb)
    return llm, judge_llm, agents, rm, rw
