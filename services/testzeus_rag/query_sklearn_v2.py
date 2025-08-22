import argparse, json, pathlib
import numpy as np

def load_meta(meta_path):
    metas = []
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def l2_normalize(mat, eps=1e-12):
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return mat / norms

def main(args):
    idx_dir = pathlib.Path(args.index_dir)
    metas = load_meta(idx_dir / "meta.jsonl")
    vecs = np.load(idx_dir / "embeddings.npy")  # float64, normalized rows

    if vecs.ndim != 2 or vecs.shape[0] == 0:
        raise SystemExit("embeddings.npy is empty or malformed. Rebuild the index.")

    # Encode and L2-normalize query
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)
    q = model.encode([args.query], convert_to_numpy=True, normalize_embeddings=False).astype("float64")
    q = l2_normalize(q)  # shape (1, d)

    # Cosine similarity = dot since both are L2-normalized
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        sims = vecs.dot(q[0])  # shape (n,)
        sims = np.nan_to_num(sims, copy=False, nan=-1.0, posinf=-1.0, neginf=-1.0)
        sims = np.clip(sims, -1.0, 1.0)

    k = min(max(args.k, 1), sims.shape[0])
    top_idx = np.argpartition(-sims, k-1)[:k]
    top_idx = top_idx[np.argsort(-sims[top_idx])]

    for rank, i in enumerate(top_idx, start=1):
        m = metas[int(i)]
        sim = float(sims[int(i)])
        title = m.get("title","")
        url = m.get("url","")
        txt = (m.get("text","") or "").replace("\n"," ")
        print(f"[{rank}] sim={sim:.4f} | {title} | {url}")
        print(txt[:500] + ("..." if len(txt) > 500 else ""))
        print("-"*80)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--query", required=True)
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()
    main(args)
