"""AOP's solvability reward model (paper section 4.2, Eq. 2-4).

M_theta(q, d) = MLP([E(q); E(d)]),   E = frozen all-MiniLM-L6-v2 (384-d)
MLP: 768 -> 256 -> 64 -> 1 (ReLU), trained with MSE on scorer grades,
batch 32, lr 1e-3, 50 epochs (paper defaults).

The MLP is written in NumPy (with Adam) so it trains in seconds on a CPU and needs no
PyTorch. Embeddings come from sentence-transformers when installed; otherwise a
hashing embedder is used (only meant for tests / the mock pipeline).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------- embedders
class HashEmbedder:
    """Bag-of-words feature hashing. A stand-in when sentence-transformers is absent."""
    dim = 384
    name = "hash-384"

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in re.findall(r"[a-z0-9]+", t.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0 if (h >> 9) & 1 else -1.0
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(n, 1e-8)


class STEmbedder:
    dim = 384

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.name = model_name

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True,
                                            show_progress_bar=False), dtype=np.float32)


class CachedEmbedder:
    def __init__(self, base):
        self.base, self.dim, self.name = base, base.dim, base.name
        self._cache: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()

    def encode(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            vecs = self.base.encode(missing)
            with self._lock:
                for t, v in zip(missing, vecs):
                    self._cache[t] = v
        return np.stack([self._cache[t] for t in texts])


def make_embedder(kind: str = "auto"):
    if kind in ("auto", "minilm"):
        try:
            return CachedEmbedder(STEmbedder())
        except Exception:
            if kind == "minilm":
                raise
            print("[reward_model] sentence-transformers not available; using HashEmbedder")
    return CachedEmbedder(HashEmbedder())


# ---------------------------------------------------------------- MLP
class MLP:
    def __init__(self, sizes=(768, 256, 64, 1), seed: int = 0):
        rng = np.random.default_rng(seed)
        self.W = [rng.normal(0, np.sqrt(2 / a), (a, b)).astype(np.float32) for a, b in zip(sizes, sizes[1:])]
        self.b = [np.zeros(b, dtype=np.float32) for b in sizes[1:]]

    def forward(self, x, keep=False):
        acts = [x]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            x = x @ W + b
            if i < len(self.W) - 1:
                x = np.maximum(x, 0)
            acts.append(x)
        return (x[:, 0], acts) if keep else x[:, 0]

    def fit(self, X, y, epochs=50, batch=32, lr=1e-3, seed=0, val=None, verbose=True,
            weight_decay=0.0, patience=None):
        """Adam(W) on MSE. With ``val`` and ``patience``, stops early and restores the
        weights with the lowest validation MSE (guards against over-fitting)."""
        rng = np.random.default_rng(seed)
        params = self.W + self.b
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        t = 0
        history = []
        self.b[-1][:] = float(np.mean(y))          # start from predicting the mean
        best, best_state, bad = float("inf"), None, 0
        for ep in range(epochs):
            idx = rng.permutation(len(X))
            for s in range(0, len(X), batch):
                bi = idx[s:s + batch]
                pred, acts = self.forward(X[bi], keep=True)
                g = (2 * (pred - y[bi]) / len(bi))[:, None]          # dMSE/dout
                gW, gb = [None] * len(self.W), [None] * len(self.b)
                for L in range(len(self.W) - 1, -1, -1):
                    gW[L] = acts[L].T @ g
                    gb[L] = g.sum(0)
                    if L > 0:
                        g = (g @ self.W[L].T) * (acts[L] > 0)
                grads = gW + gb
                t += 1
                for p, gr, mi, vi in zip(params, grads, m, v):
                    mi *= 0.9; mi += 0.1 * gr
                    vi *= 0.999; vi += 0.001 * gr * gr
                    p -= lr * (mi / (1 - 0.9 ** t)) / (np.sqrt(vi / (1 - 0.999 ** t)) + 1e-8)
                if weight_decay:                      # decoupled weight decay on weights only
                    for W in self.W:
                        W *= 1 - lr * weight_decay
            tr = float(np.mean((self.forward(X) - y) ** 2))
            row = {"epoch": ep + 1, "train_mse": tr}
            if val is not None:
                row["val_mse"] = float(np.mean((self.forward(val[0]) - val[1]) ** 2))
            history.append(row)
            if verbose and (ep + 1) % 10 == 0:
                print(row)
            if val is not None and patience:
                if row["val_mse"] < best - 1e-4:
                    best, bad = row["val_mse"], 0
                    best_state = ([W.copy() for W in self.W], [b.copy() for b in self.b], ep + 1)
                else:
                    bad += 1
                    if bad >= patience:
                        break
        if best_state is not None:
            self.W, self.b = best_state[0], best_state[1]
            if verbose:
                print(f"early stopping: restored epoch {best_state[2]} (val_mse={best:.3f})")
        return history


class RewardModel:
    """Predicts how well agent (description d) will solve sub-task q, on the scorer's 0-5 scale."""

    def __init__(self, embedder, mlp: MLP | None = None):
        self.emb = embedder
        self.mlp = mlp or MLP((2 * embedder.dim, 256, 64, 1))

    def features(self, tasks: list[str], descs: list[str]) -> np.ndarray:
        return np.concatenate([self.emb.encode(tasks), self.emb.encode(descs)], axis=1)

    def score(self, task: str, desc: str) -> float:
        return float(self.mlp.forward(self.features([task], [desc]))[0])

    def score_all(self, task: str, agents: dict[str, str]) -> dict[str, float]:
        names = list(agents)
        s = self.mlp.forward(self.features([task] * len(names), [agents[n] for n in names]))
        return {n: float(x) for n, x in zip(names, s)}

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, *self.mlp.W, *self.mlp.b)
        Path(path + ".json").write_text(encoding="utf-8", data=json.dumps({"embedder": self.emb.name,
                                                    "n_layers": len(self.mlp.W)}))

    @classmethod
    def load(cls, path: str, embedder):
        meta = json.loads(Path(path + ".json").read_text(encoding="utf-8"))
        if meta["embedder"] != embedder.name:
            raise ValueError(f"reward model was trained with {meta['embedder']}, "
                             f"but embedder is {embedder.name}")
        arr = np.load(path if path.endswith(".npz") else path + ".npz")
        k = meta["n_layers"]
        mlp = MLP.__new__(MLP)
        mlp.W = [arr[f"arr_{i}"] for i in range(k)]
        mlp.b = [arr[f"arr_{i}"] for i in range(k, 2 * k)]
        return cls(embedder, mlp)


class RepresentativeWorks:
    """Per-agent memory of sub-tasks the agent solved well (paper section 4.3, Eq. 5)."""

    def __init__(self, embedder, novelty_threshold: float = 0.9):
        self.emb = embedder
        self.novelty = novelty_threshold
        self.works: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def similarity(self, task: str, agent: str) -> tuple[float, list[str]]:
        """max cosine similarity to the agent's works, plus the top-3 most similar works."""
        works = self.works.get(agent) or []
        if not works:
            return 0.0, []
        q = self.emb.encode([task])[0]
        W = self.emb.encode(works)
        sims = W @ q
        order = np.argsort(-sims)[:3]
        return float(sims[order[0]]), [works[i] for i in order]

    def add(self, task: str, agent: str) -> bool:
        with self._lock:
            sim, _ = self.similarity(task, agent)
            if sim >= self.novelty:
                return False
            self.works.setdefault(agent, []).append(task)
            return True

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.works, indent=1, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str, embedder, novelty_threshold: float = 0.9):
        rw = cls(embedder, novelty_threshold)
        rw.works = json.loads(Path(path).read_text(encoding="utf-8"))
        return rw
