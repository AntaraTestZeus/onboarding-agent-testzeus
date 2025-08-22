import argparse, json, pathlib
import numpy as np
import faiss

def load_meta(meta_path):
    metas = []
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def main(args):
    index = faiss.read_index(str(pathlib.Path(args.index_dir) / "index.faiss"))
    metas = load_meta(pathlib.Path(args.index_dir) / "meta.jsonl")

    # naive prompt encoder by averaging word vectors is NOT used — we rely on the same model embedding pipeline.
    # for simplicity, we'll load the same SentenceTransformer used for indexing:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)
    qvec = model.encode([args.query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")

    D, I = index.search(qvec, args.k)
    for rank, (score, idx) in enumerate(zip(D[0], I[0]), start=1):
        m = metas[int(idx)]
        print(f"[{rank}] score={float(score):.4f} | {m['title']} | {m['url']}")
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
