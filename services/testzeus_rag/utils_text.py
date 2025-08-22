import re
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+\n", "\n", re.sub(r"[ \t]+", " ", s)).strip()
