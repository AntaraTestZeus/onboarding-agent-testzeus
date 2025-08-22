import argparse, json, pathlib, hashlib
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import numpy as np
import joblib

MIN_CH_LEN = 30  # drop very short/empty chunks

def chunk_text(text, size=800, overlap=120):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        j = min(len(words), i + size)
        chunk = " ".join(words[i:j]).strip()
        if chunk:
            chunks.append(chunk)
        if j == len(words): break
        i = max(j - overlap, i + 1)
    return chunks

def l2_normalize(mat, eps=1e-12):
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return mat / norms

def main(args):
    in_path = pathlib.Path(args.in_path)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(args.model)

    meta_records = []
    texts = []
    seen_hashes = set()

    with in_path.open("r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Reading"):
            obj = json.loads(line)
            chunks = chunk_text(obj.get("text",""), size=args.chunk_size, overlap=args.chunk_overlap)
            for idx, ch in enumerate(chunks):
                if len(ch) < MIN_CH_LEN:
                    continue
                # Deduplicate exact text (helps with repeated hero sections)
                h = hashlib.md5(ch.encode("utf-8")).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                meta = {
                    "url": obj.get("url",""),
                    "title": obj.get("title", ""),
                    "chunk_id": idx,
                    "text": ch
                }
                meta_records.append(meta)
                texts.append(ch)

    if not texts:
        raise SystemExit("No valid chunks found. Check your crawl or lower MIN_CH_LEN.")

    vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=True, batch_size=64, normalize_embeddings=False).astype("float64")
    # Clean numeric issues and normalize
    vecs = np.nan_to_num(vecs, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    vecs = l2_normalize(vecs)

    # Persist
    np.save(out_dir / "embeddings.npy", vecs)
    with open(out_dir / "meta.jsonl", "w", encoding="utf-8") as mf:
        for m in meta_records:
            mf.write(json.dumps(m, ensure_ascii=False) + "\n")

    # Save a tiny info file
    info = {
        "model": args.model,
        "num_chunks": int(vecs.shape[0]),
        "dim": int(vecs.shape[1])
    }
    with open(out_dir / "info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"Saved index with {vecs.shape[0]} normalized embeddings (float64) to {out_dir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--chunk-size", type=int, default=800)
    ap.add_argument("--chunk-overlap", type=int, default=120)
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()
    main(args)
