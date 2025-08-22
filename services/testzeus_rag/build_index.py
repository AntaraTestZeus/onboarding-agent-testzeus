import argparse, json, os, pathlib
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

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
    all_vecs = []

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

    texts = [m["text"] for m in meta_records]
    vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=True, batch_size=64, normalize_embeddings=True)
    all_vecs.append(vecs)

    mat = np.vstack(all_vecs).astype("float32")
    index = faiss.IndexFlatIP(mat.shape[1])
    index.add(mat)

    faiss.write_index(index, str(out_dir / "index.faiss"))
    with open(out_dir / "meta.jsonl", "w", encoding="utf-8") as mf:
        for m in meta_records:
            mf.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"Saved FAISS index to {out_dir}/index.faiss with {mat.shape[0]} vectors.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="raw.jsonl from crawler")
    ap.add_argument("--out-dir", required=True, help="output dir for FAISS + metadata")
    ap.add_argument("--chunk-size", type=int, default=800)
    ap.add_argument("--chunk-overlap", type=int, default=120)
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()
    main(args)
