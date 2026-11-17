"""Course-material ingestion: approved PDFs -> pages -> de-duplicated slide chunks.

Two stages, both reproducible:

  1. PDF -> data/slides.json   (python -m app.ingest --from-pdfs)
     Reads ONLY files listed in course_materials/manifest.json, verifies each file's
     sha256, skips 'revoked' sources, and records page-level text with pypdf.
  2. slides.json -> data/chunks.json   (python -m app.ingest)
     Lecture PDFs are LaTeX Beamer decks where one logical slide is exported as many
     near-identical "animation" pages (Kruskal's algorithm = 7 pages). Consecutive
     near-duplicate pages are merged into ONE chunk that keeps the fullest text and
     records the page range for citations. Each chunk carries its source's permission
     status from the manifest.

Embeddings are computed at server start from chunks.json (app/embeddings.py), so there is
no pickled model to go stale across scikit-learn versions.

Run:
  python -m app.ingest                 # rebuild chunks from data/slides.json
  python -m app.ingest --from-pdfs     # re-extract approved/pending PDFs, then rebuild chunks
  python -m app.ingest --check         # verify manifest hashes only
"""
from pathlib import Path
import argparse, hashlib, json, re, sys

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / 'course_materials'
MANIFEST = MATERIALS / 'manifest.json'
LIGATURES = {'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl'}


# ---------------- manifest / permission boundary ----------------
def load_manifest(path=MANIFEST):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    for s in data['sources']:
        if s.get('status') not in ('approved', 'pending', 'revoked'):
            raise ValueError(f"manifest: invalid status for {s.get('file')!r}")
    return data


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 16), b''):
            h.update(block)
    return h.hexdigest()


def check_manifest(materials=MATERIALS, manifest=None):
    """Return (ok_sources, problems). Unlisted PDFs and hash mismatches are problems."""
    manifest = manifest or load_manifest(materials / 'manifest.json')
    listed = {s['file']: s for s in manifest['sources']}
    problems, ok = [], []
    for pdf in sorted(Path(materials).rglob('*.pdf')):
        rel = pdf.relative_to(materials).as_posix()
        if rel not in listed:
            problems.append(f'UNLISTED (refused): {rel}')
    for name, s in listed.items():
        p = Path(materials) / name
        if not p.exists():
            problems.append(f'MISSING: {name}')
        elif sha256(p) != s['sha256']:
            problems.append(f'HASH MISMATCH (refused): {name}')
        elif s['status'] == 'revoked':
            problems.append(f'REVOKED (skipped): {name}')
        else:
            ok.append(s)
    return ok, problems


# ---------------- PDF extraction ----------------
def _pages_text(path):
    """Per-page text. Prefer poppler's pdftotext (keeps spaces around italic math variables), then
    pdfplumber, then pypdf (which glues e.g. "let P" -> "letP")."""
    import shutil, subprocess
    if shutil.which('pdftotext'):
        out = subprocess.run(['pdftotext', str(path), '-'], capture_output=True, text=True, check=True).stdout
        return out.split('\f')[:-1] if out.endswith('\f') else out.split('\f')
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return [pg.extract_text() or '' for pg in pdf.pages]
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise SystemExit('Install poppler (pdftotext), pdfplumber or pypdf to ingest PDFs') from e
    return [pg.extract_text() or '' for pg in PdfReader(str(path)).pages]


def extract_pdf(path, unit):
    slug = re.sub(r'[^a-z0-9]+', '-', unit.lower()).strip('-')
    pages = []
    for i, text in enumerate(_pages_text(path), 1):
        text = re.sub(r'\s+', ' ', text).strip()        # same shape as the original slides.json
        if text:
            pages.append({'id': f'{slug}-{i}', 'unit': unit, 'file': Path(path).name, 'page': i, 'text': text})
    return pages


def unglue(pages, min_count=2):
    """pypdf sometimes drops the space between two words ("calledfeasible"). Split a lowercase
    token that never occurs on its own when it is exactly two words that DO occur elsewhere."""
    from collections import Counter
    vocab = Counter(w for p in pages for w in re.findall(r'[a-z]+', p['text']))

    def fix(m):
        w = m.group(0)
        if vocab[w] > 1 or len(w) < 9:
            return w
        for i in range(3, len(w) - 2):
            a, b = w[:i], w[i:]
            if len(a) >= 2 and len(b) >= 3 and ((vocab[a] >= min_count and vocab[b] >= min_count)
                                                or min(vocab[a], vocab[b]) >= 1 and max(vocab[a], vocab[b]) >= 5):
                return f'{a} {b}'
        return w
    for p in pages:
        p['text'] = re.sub(r'\b[a-z]{9,}\b', fix, p['text'])
    return pages


def build_slides_from_pdfs(materials=MATERIALS, out=ROOT / 'data' / 'slides.json'):
    ok, problems = check_manifest(materials)
    for p in problems:
        print('  !', p)
    slides = []
    for s in ok:
        if s.get('kind', 'lecture') != 'lecture':
            continue
        pages = extract_pdf(Path(materials) / s['file'], s['unit'])
        print(f"  {s['file']}: {len(pages)} text pages  [{s['status']}]")
        slides += pages
    unglue(slides)
    Path(out).write_text(json.dumps(slides, ensure_ascii=False, indent=1), encoding='utf-8')
    return slides


# ---------------- assignments -> exercises ----------------
EXERCISE_HEAD = re.compile(r'Exercise\s+(\d+)\s*[ .]{5,}\s*(\d+)\s*points?')
BOILERPLATE = re.compile(r'Page \d+ of \d+')
FIGURE = re.compile(r'\b(figure|shown below|graph below|following (?:bipartite |directed |weighted )?graph|floor plan|'
                    r'with costs below|weighted graph H shown)\b', re.I)


def extract_text_best(path):
    """Assignments are math-heavy; pypdf glues italic variables to words ("ofndifferent").
    Prefer poppler's pdftotext, then pdfplumber, then pypdf."""
    import shutil, subprocess
    if shutil.which('pdftotext'):
        return subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, text=True, check=True).stdout
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return '\n'.join(pg.extract_text() or '' for pg in pdf.pages)
    except ImportError:
        from pypdf import PdfReader
        return '\n'.join(pg.extract_text() or '' for pg in PdfReader(str(path)).pages)


def split_exercises(text, assignment):
    text = BOILERPLATE.sub(' ', text)
    opt_at = text.find('Optional exercises')
    heads = list(EXERCISE_HEAD.finditer(text))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.end():end]
        if opt_at != -1 and h.start() < opt_at < end:
            body = body[:opt_at - h.end()]
        body = re.sub(r'[ \t]+', ' ', body)
        body = re.sub(r'\n\s*\n+', '\n', body).strip()
        out.append({'id': f'{assignment}.E{h.group(1)}', 'assignment': assignment, 'number': int(h.group(1)),
                    'points': int(h.group(2)), 'optional': opt_at != -1 and h.start() > opt_at,
                    'has_figure': bool(FIGURE.search(body)), 'text': body})
    return out


def build_exercises(materials=MATERIALS, out=ROOT / 'data' / 'exercises.json'):
    ok, _ = check_manifest(materials)
    mapping = json.loads((ROOT / 'data' / 'exercise_map.json').read_text(encoding='utf-8'))
    exercises = []
    for s in ok:
        if s.get('kind') != 'assignment':
            continue
        a = 'A' + re.search(r'(\d+)', Path(s['file']).name).group(1)
        for ex in split_exercises(extract_text_best(Path(materials) / s['file']), a):
            amap = mapping.get(a, {})
            ex['concepts'] = amap.get(str(ex['number']), amap.get('*'))
            ex['covered'] = bool(ex['concepts'])
            ex['source'] = s['file']
            ex['permission'] = s['status']
            exercises.append(ex)
    Path(out).write_text(json.dumps(exercises, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(exercises)} exercises written to {out}')
    return exercises


# ---------------- chunking ----------------
def clean(text: str) -> str:
    for a, b in LIGATURES.items():
        text = text.replace(a, b)
    text = text.replace('▶', '\n• ')           # Beamer bullet -> real bullet
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
    head = re.split(r'•|\s1\.\s|\s(?:Theorem|Lemma|Proposition|Corollary)\b', text, maxsplit=1)[0]
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


def build(slides_path=ROOT / 'data' / 'slides.json', out=ROOT / 'data' / 'chunks.json', manifest=None):
    slides = json.loads(Path(slides_path).read_text(encoding='utf-8'))
    try:
        manifest = manifest or load_manifest()
        status = {s['file']: s['status'] for s in manifest['sources']}
    except FileNotFoundError:
        status = {}
    chunks, current = [], None
    for s in slides:
        if status.get(s['file']) == 'revoked':
            continue
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
        c['permission'] = status.get(c['file'], 'unlisted')
    Path(out).write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(slides)} pages -> {len(chunks)} chunks written to {out}')
    return chunks


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--from-pdfs', action='store_true', help='re-extract text from manifest-listed PDFs first')
    ap.add_argument('--check', action='store_true', help='verify manifest hashes and exit')
    a = ap.parse_args(argv)
    if a.check:
        ok, problems = check_manifest()
        for s in ok:
            print(f"  ok  {s['file']}  [{s['status']}]")
        for p in problems:
            print('  !', p)
        return 1 if any(p.startswith(('HASH', 'MISSING')) for p in problems) else 0
    if a.from_pdfs:
        build_slides_from_pdfs()
        build_exercises()
    build()
    return 0


if __name__ == '__main__':
    sys.exit(main())
