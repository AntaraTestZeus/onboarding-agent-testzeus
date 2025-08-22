import argparse, json, pathlib
import numpy as np
from sklearn.neighbors import NearestNeighbors
import joblib

def load_meta(meta_path):
    metas = []
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def main(args):
    idx_dir = pathlib.Path(args.index_dir)
    nn: NearestNeighbors = joblib.load(idx_dir / "nn.joblib")
    metas = load_meta(idx_dir / "meta.jsonl")
    vecs = np.load(idx_dir / "embeddings.npy")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)
    qvec = model.encode([args.query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")

    distances, indices = nn.kneighbors(qvec, n_neighbors=args.k, return_distance=True)
    for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), start=1):
        m = metas[int(idx)]
        # cosine distance -> similarity = 1 - distance
        sim = 1 - float(dist)
        print(f"[{rank}] sim={sim:.4f} | {m['title']} | {m['url']}")
        print(m["text"][:500].replace("\n"," ") + ("..." if len(m["text"])>500 else ""))
        print("-"*80)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--query", required=True)
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()
    main(args)
