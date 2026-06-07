import re
from functools import lru_cache
from pathlib import Path

OCR_UI_NOISE = {
    "discovered place",
    "shanghai",
    "china",
    "other",
    "screenshot",
    "unverified",
    "unveriiled",
    "hidden gem",
    "extracted description",
    "extracted desc ription",
    "aesthetic note",
    "why it was saved",
    "why it was saved:",
}

OCR_UI_PHRASES = (
    "screenshot inspiration:",
    "extracted from screenshot",
    "visually inspiring travel spot",
    "extracted desc",
)


@lru_cache(maxsize=1)
def _reader():
    import easyocr

    return easyocr.Reader(["ru", "en"], gpu=False, verbose=False)


def _is_noise_line(text: str) -> bool:
    lower = text.strip().lower()
    if not lower or lower in OCR_UI_NOISE:
        return True
    if any(phrase in lower for phrase in OCR_UI_PHRASES):
        return True
    if re.fullmatch(r"[\d%./\s:;,-]+", lower):
        return True
    return False


def normalize_place_name(name: str) -> str:
    cleaned = name.strip().strip("\"'«»")
    key = re.sub(r"\s+", "", cleaned.lower())
    fixes = {
        "zhuiijiajiao": "Zhujiajiao",
        "zhujiiajiao": "Zhujiajiao",
        "zhujiajiao": "Zhujiajiao",
    }
    if key in fixes:
        return fixes[key]
    if cleaned.isupper() and len(cleaned) > 3:
        return cleaned.title()
    return cleaned


def extract_text_from_image(image_path: str | Path) -> str:
    path = Path(image_path)
    if not path.exists():
        return ""
    try:
        results = _reader().readtext(str(path))
    except Exception:
        return ""

    lines: list[str] = []
    for _bbox, text, conf in results:
        if conf < 0.35:
            continue
        cleaned = text.strip()
        if _is_noise_line(cleaned):
            continue
        lines.append(cleaned)
    return "\n".join(lines)
