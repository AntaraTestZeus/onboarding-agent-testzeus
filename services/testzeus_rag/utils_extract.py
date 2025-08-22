import re

def strip_boilerplate(text: str) -> str:
    # collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # drop very short lines and duplicate lines (headers/footers/hero repeats)
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
