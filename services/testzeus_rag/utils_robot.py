import aiohttp
from urllib.parse import urljoin, urlparse
import re
import xml.etree.ElementTree as ET

class RobotsHelper:
    def __init__(self, domain, user_agent="*"):
        self.domain = domain.rstrip("/")
        self.user_agent = user_agent
        self.rules = []
        self.fetched = False

    async def load(self):
        robots_url = urljoin(self.domain, "/robots.txt")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=15) as resp:
                    if resp.status == 200:
                        txt = await resp.text()
                        self.parse(txt)
        except Exception:
            pass
        self.fetched = True

    def parse(self, text):
        ua = None
        allows, disallows = [], []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"): 
                continue
            if line.lower().startswith("user-agent:"):
                ua = line.split(":",1)[1].strip()
            elif line.lower().startswith("allow:") and (ua=="*" or ua==self.user_agent):
                allows.append(line.split(":",1)[1].strip())
            elif line.lower().startswith("disallow:") and (ua=="*" or ua==self.user_agent):
                disallows.append(line.split(":",1)[1].strip())
        self.rules = (allows, disallows)

    def allowed(self, url):
        # very simple check: disallow wins if path startswith any disallowed rule
        if not self.rules: 
            return True
        allows, disallows = self.rules
        path = urlparse(url).path or "/"
        for d in disallows:
            if d and path.startswith(d):
                # check if any allow overrides
                for a in allows:
                    if a and path.startswith(a):
                        return True
                return False
        return True

    async def fetch_sitemap(self, sitemap_url):
        urls = set()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url, timeout=20) as resp:
                    if resp.status != 200:
                        return urls
                    xml = await resp.text()
        except Exception:
            return urls

        try:
            root = ET.fromstring(xml)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            # urlset
            for u in root.findall(".//sm:url/sm:loc", ns):
                urls.add(u.text.strip())
            # sitemap index
            for sm in root.findall(".//sm:sitemap/sm:loc", ns):
                urls |= await self.fetch_sitemap(sm.text.strip())
        except Exception:
            pass
        return urls

async def discover_sitemaps(domain, robots: RobotsHelper):
    candidates = set()
    # robots.txt <Sitemap: ...>
    robots_url = domain.rstrip("/") + "/robots.txt"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(robots_url, timeout=15) as resp:
                if resp.status == 200:
                    txt = await resp.text()
                    for line in txt.splitlines():
                        if line.lower().startswith("sitemap:"):
                            candidates.add(line.split(":",1)[1].strip())
    except Exception:
        pass
    # default guesses
    for path in ("/sitemap.xml", "/sitemap_index.xml"):
        candidates.add(domain.rstrip("/") + path)
    return list(candidates)
