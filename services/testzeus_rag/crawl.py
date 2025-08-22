import argparse, asyncio, json, time
from urllib.parse import (
    urldefrag, urljoin, urlparse, urlunparse, parse_qsl, urlencode
)
import aiohttp
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
import tldextract
import pathlib
import os

from utils_extract import extract_main_text
from utils_robot import RobotsHelper, discover_sitemaps

DEFAULT_UA = "TestZeus-RAG-Crawler/1.0 (+https://testzeus.com)"
SEEN = set()

# Try to import a stronger boilerplate stripper; fall back to a simple one if missing
try:
    from utils_extract import strip_boilerplate as _strip_boilerplate
except Exception:
    import re
    def _strip_boilerplate(text: str) -> str:
        # collapse whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        # drop very short/duplicate lines
        seen = set()
        kept = []
        for line in text.splitlines():
            line = line.strip()
            if len(line.split()) < 3:
                continue
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            kept.append(line)
        return "\n".join(kept)

TRACKING_KEYS = {
    "utm_source","utm_medium","utm_campaign","utm_term","utm_content",
    "gclid","fbclid","mc_cid","mc_eid"
}

def same_reg_domain(url, root):
    u = tldextract.extract(url)
    r = tldextract.extract(root)
    return (u.domain, u.suffix) == (r.domain, r.suffix)

def clean_url(href, base):
    """Resolve relative hrefs, normalize host (strip leading www.), drop fragments
    and common tracking params, ensure path is non-empty.
    """
    if not href:
        return None
    href = urljoin(base, href)
    href = urldefrag(href)[0]  # drop #fragment
    p = urlparse(href)
    if p.scheme not in ("http", "https"):
        return None

    # normalize host
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # drop common tracking params
