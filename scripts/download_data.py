"""Download HuskyQA (and DROP*/IIRC*) from the HUSKY authors' HuggingFace page and
convert to data/<name>/<split>.jsonl with fields: id, question, answer.

    python scripts/download_data.py            # list what's available + download huskyqa
    python scripts/download_data.py --all      # also drop / iirc

Needs: pip install huggingface_hub pandas pyarrow
If the automatic route fails, download the files by hand from
https://huggingface.co/agent-husky and use --from-file.
"""
import argparse
import json
import sys
from pathlib import Path


def to_rows(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if path.suffix == ".json":
        text = path.read_text(encoding="utf-8")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:  # a .json file that is really JSON Lines
            return [json.loads(l) for l in text.splitlines() if l.strip()]
        if isinstance(obj, list):
            return obj
        return obj.get("data", []) if isinstance(obj, dict) else []
    if path.suffix in (".parquet", ".csv"):
        import pandas as pd
        df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        return df.to_dict("records")
    return []


def standardize(rows: list[dict]) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        q = r.get("question") or r.get("query") or r.get("input")
        a = r.get("answer") if r.get("answer") is not None else (r.get("answers") or r.get("output") or r.get("label"))
        if q is None or a is None:
            continue
        if hasattr(a, "tolist"):
            a = a.tolist()
        out.append({"id": str(r.get("id", r.get("index", i))), "question": str(q), "answer": a})
    return out


def write(rows, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows):5d} rows -> {dest}")


def guess_split(name: str) -> str:
    n = name.lower()
    return "train" if "train" in n else ("dev" if "dev" in n or "val" in n else "test")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also download drop and iirc")
    ap.add_argument("--author", default="agent-husky")
    ap.add_argument("--out", default="data")
    ap.add_argument("--from-file", nargs=3, metavar=("FILE", "DATASET", "SPLIT"),
                    help="convert a manually downloaded file, e.g. huskyqa_train.json huskyqa train")
    args = ap.parse_args()

    if args.from_file:
        f, ds, split = args.from_file
        write(standardize(to_rows(Path(f))), Path(args.out) / ds / f"{split}.jsonl")
        return

    from huggingface_hub import HfApi, snapshot_download
    api = HfApi()
    repos = [d.id for d in api.list_datasets(author=args.author)]
    print("datasets by", args.author, ":", repos)
    wanted = ["huskyqa"] + (["drop", "iirc"] if args.all else [])
    found = False
    for repo in repos:
        key = next((w for w in wanted if w in repo.lower().replace("-", "").replace("_", "")), None)
        if not key:
            continue
        found = True
        local = Path(snapshot_download(repo_id=repo, repo_type="dataset"))
        files = [p for p in local.rglob("*") if p.suffix in (".jsonl", ".json", ".parquet", ".csv")]
        print(f"{repo}: files {[p.name for p in files]}")
        for p in files:
            rows = standardize(to_rows(p))
            if rows:
                write(rows, Path(args.out) / key / f"{guess_split(p.name)}.jsonl")
            else:
                print(f"  skipped {p.name}: no question/answer rows found")
    if not found:
        sys.exit("No matching dataset found. Download manually from https://huggingface.co/agent-husky "
                 "and use --from-file.")
    print("\nNote: the public HuskyQA release has only the 292-question test set. The reward model "
          "is trained on data/rm_train/train.jsonl instead (see data/rm_train/README.md).")


if __name__ == "__main__":
    main()
