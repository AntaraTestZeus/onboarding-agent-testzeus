import argparse, json, pathlib
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.neighbors import NearestNeighbors
import joblib

def chunk_text(text, size=800, overlap=120):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        j = min(len(words), i + size)
        chunk = " ".join(words[i:j])
        chunks.append(chunk)
        if j == len(words): break
        i = max(j - overlap, i + 1)
    return chunks

def main(args):
    in_path = pathlib.Path(args.in_path)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(args.model)

    meta_records = []
    texts = []
    with in_path.open("r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Reading"):
            obj = json.loads(line)
            chunks = chunk_text(obj["text"], size=args.chunk_size, overlap=args.chunk_overlap)
            for idx, ch in enumerate(chunks):
                meta = {
                    "url": obj["url"],
                    "title": obj.get("title", ""),
                    "chunk_id": idx,
                    "text": ch
                }
                meta_records.append(meta)
                texts.append(ch)

    # Embed
    vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=True, batch_size=64, normalize_embeddings=True).astype("float32")

    # Build NearestNeighbors (cosine distance)
    nn = NearestNeighbors(metric="cosine", algorithm="auto")
    nn.fit(vecs)

    # Persist
    joblib.dump(nn, out_dir / "nn.joblib")
    np.save(out_dir / "embeddings.npy", vecs)
    with open(out_dir / "meta.jsonl", "w", encoding="utf-8") as mf:
        for m in meta_records:
            mf.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"Saved scikit-learn NN index with {vecs.shape[0]} vectors at {out_dir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--chunk-size", type=int, default=800)
    ap.add_argument("--chunk-overlap", type=int, default=120)
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()
    main(args)
