"""Build data/chunks.json from data/slides.json.

Problem this fixes: lecture PDFs are LaTeX Beamer decks where one logical slide is
exported as many near-identical "animation" pages (e.g. Kruskal's algorithm = 7 pages).
Indexing every page makes retrieval return the same slide several times and wastes the
top-k budget. Here consecutive near-duplicate pages are merged into ONE chunk that keeps
the fullest text and records the page range for citations.

Run:  python -m app.ingest
"""
from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
LIGATURES = {'\ufb00': 'ff', '\ufb01': 'fi', '\ufb02': 'fl', '\ufb03': 'ffi', '\ufb04': 'ffl'}


def clean(text: str) -> str:
    for a, b in LIGATURES.items():
        text = text.replace(a, b)
    text = text.replace('\u25b6', '\n\u2022 ')           # Beamer bullet -> real bullet
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)
    return text.strip()


def words(text: str) -> set:
    return set(re.findall(r'[a-z0-9]+', text.lower()))


def similar(a: str, b: str, threshold: float = 0.72) -> bool:
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= threshold


def title_of(text: str) -> str:
    """Slide title = text before the first bullet / numbered step (extraction has no real title field)."""
    head = re.split(r'\u2022|\s1\.\s|\s(?:Theorem|Lemma|Proposition|Corollary)\b', text, maxsplit=1)[0]
    rep = re.match(r'^(.{3,40}?)\s+\1\b', head)   # Beamer repeats the title inside the box
    if rep:
        head = rep.group(1)
    if len(head) > 45:   # bullet-less slide: short title followed by a sentence
        m = re.match(r'(.{3,40}?)\s+(?=(?:There|We|The|If|For|Let|Suppose|Given|How|Consider|A|An|In|Why|Beginning|Define)\b)', head)
        if m:
            head = m.group(1)
    return re.sub(r'\s+', ' ', head).strip()[:70]


def same_title(a: str, b: str) -> bool:
    ta, tb = title_of(a).lower().split()[:4], title_of(b).lower().split()[:4]
    return ta == tb


def build():
    slides = json.loads((ROOT / 'data' / 'slides.json').read_text(encoding='utf-8'))
    chunks, current = [], None
    for s in slides:
        text = clean(s['text'])
        if len(text) < 25:                                  # blank / figure-only pages
            continue
        if (current and current['file'] == s['file'] and s['page'] - current['page_end'] <= 2
                and same_title(current['text'], text) and similar(current['text'], text)):
            current['page_end'] = s['page']
            if len(text) > len(current['text']):            # keep the fullest animation frame
                current['text'] = text
            continue
        current = {'unit': s['unit'], 'file': s['file'], 'page_start': s['page'],
                   'page_end': s['page'], 'text': text}
        chunks.append(current)
    for i, c in enumerate(chunks):
        c['id'] = i
        c['page'] = c['page_start']
        c['title'] = title_of(c['text'])
        c['pages'] = (f"{c['page_start']}" if c['page_start'] == c['page_end']
                      else f"{c['page_start']}-{c['page_end']}")
    out = ROOT / 'data' / 'chunks.json'
    out.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(slides)} pages -> {len(chunks)} chunks written to {out}')
    return chunks


if __name__ == '__main__':
    build()
