"""Check that the search backend works from your machine before long runs.

    python scripts/check_search.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop.search import Search            # noqa: E402
from aop.system import load_dotenv       # noqa: E402
import os                                # noqa: E402

load_dotenv()
s = Search(os.getenv("SEARCH_BACKEND", "wikipedia"), cache_path=None)
queries = ["population of Nigeria 2022", "number of members of the French Senate",
           "Kevin De Bruyne Premier League goals 2022-23", "area of Pennsylvania square miles",
           "Fuwa Olympic mascots"]
t0 = time.time()
for q in queries:
    out = s(q)
    status = "ERROR" if out.startswith("[search error") else "ok"
    print(f"[{status}] {q}\n    {out[:160].replace(chr(10), ' ')}")
print(f"\n{s.stats} in {time.time() - t0:.1f}s")
print("All good." if s.stats["error"] == 0 else f"Search is failing: {s.last_error}")
