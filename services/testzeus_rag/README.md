# TestZeus.com → RAG (FAISS) Starter Kit

This starter kit lets you **crawl testzeus.com**, **clean & chunk** the pages, **embed with Sentence-Transformers**, and **index in FAISS**. It also ships a tiny **query script** to run retrieval locally.

> Tip: Always respect the site's `robots.txt` and Terms. Default settings are gentle (2 req/s, 1 concurrent).

## 1) Install
```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 2) Crawl
By default we seed a few common entry points. You can add more in `seeds.txt` or pass `--seeds` at runtime.

```bash
python crawl.py --domain https://testzeus.com --out data/raw.jsonl --max-pages 500 --concurrency 1 --rate 0.5
```

- `--concurrency 1` and `--rate 0.5` (≈ 1 req / 2s) are conservative. You can increase once you’ve verified you’re within policy.
- The crawler auto-parses `robots.txt` and any `sitemap.xml` it discovers.

## 3) Build FAISS index
```bash
python build_index.py --in data/raw.jsonl --out-dir data/index --chunk-size 800 --chunk-overlap 120 --model sentence-transformers/all-MiniLM-L6-v2
```

This produces:
- `data/index/index.faiss` (vector store)
- `data/index/meta.jsonl` (per-chunk metadata)

## 4) Run a quick query
```bash
python query.py --index-dir data/index --k 5 --query "What does TestZeus offer?"
```

## Seeds
Add one URL per line to `seeds.txt`. Example entries are included as placeholders; adjust to real pages you want crawled.

## Notes
- If pages are JS-heavy, consider using Playwright-based rendering (not included here) or an XML/JSON feed.
- You can switch to larger models (e.g., `all-mpnet-base-v2`) for better recall at higher compute cost.
- If you later want a full RAG app, you can plug this FAISS store into your app/server and add generation with your LLM of choice.
