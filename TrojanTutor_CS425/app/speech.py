"""Making voice input usable for this course.

Browser speech recognition is tuned for everyday English, so course words come back mangled:
"Kruskal" → "crystal", "Dijkstra" → "dykstra", "dipath" → "die path", node letters → "bee", "see".
`normalize` repairs a transcript with a course vocabulary; `best_alternative` picks, among the
recogniser's alternatives, the one that reads most like a course question.
"""
import re

FIXES = [
    (r"\b(crystal'?s?|krystal'?s?|cruskal'?s?|cross ?call?s?|kruskal'?s|crew ?skull?s?|crust ?al)(?=\W*(algorithm|method|$|\?|\.|,|\s+(work|do|pick|add|skip|choose|reject|accept|use|find|check)))", 'Kruskal'),
    (r"\b(dykstra'?s?|dikstra'?s?|dijkstra'?s|dyke ?stra'?s?|dike ?stra'?s?|dextra'?s?|dijkstras|dykes? ?tra|dike's tra|dijk ?stra)\b", 'Dijkstra'),
    (r"\b(prims|prim's|prem'?s|prom'?s|prism'?s?)(?=\s+(algorithm|method|tree))", 'Prim'),
    (r"\b(belmont|bellmon|bell ?man|belman)\b", 'Bellman'),
    (r"\bfor ?bellman\b", 'Ford Bellman'),
    (r"\b(fords|ford's|fort'?s)(?=\s+algorithm)", 'Ford'),
    (r"\b(konig|koenig|kernig|conic|kenig|kanigs?|konigs|koenigs)('?s)?(?=\s+theorem)", 'König'),
    (r"\bedmonds? ?(carp|carb|cap)\b", 'Edmonds-Karp'),
    (r"\b(macs|max) ?(flow|flo)\b", 'max flow'),
    (r"\b(mint|min|men) ?cut\b", 'min cut'),
    (r"\bspinning tree", 'spanning tree'),
    (r"\b(die|dye|di) ?circuits?\b", 'dicircuit'),
    (r"\b(die|dye|di) ?paths?\b", 'dipath'),
    (r"\b(die|dye|di) ?graphs?\b", 'digraph'),
    (r"\bark(s)?\b", r'arc\1'),
    (r"\bt\.? ?s\.? ?p\b", 'TSP'),
    (r"\bm\.? ?s\.? ?t\b", 'MST'),
    (r"\bb\.? ?f\.? ?s\b", 'BFS'),
    (r"\bdelta (of )?you\b", 'delta of U'),
    (r"\bnearest neighbou?rs?\b", 'nearest neighbor'),
    (r"\btopological(ly)? (sort|sorting|order)\b", r'topological \2'),
    (r"\bauxiliary (di)?graph\b", 'auxiliary digraph'),
]

LETTERS = {'ay': 'a', 'bee': 'b', 'be': 'b', 'see': 'c', 'sea': 'c', 'cee': 'c', 'dee': 'd', 'ee': 'e', 'eff': 'f',
           'gee': 'g', 'aitch': 'h', 'jay': 'j', 'kay': 'k', 'pee': 'p', 'queue': 'q', 'cue': 'q', 'are': 'r',
           'ess': 's', 'tee': 't', 'double you': 'w'}
_L = '|'.join(sorted(map(re.escape, LETTERS), key=len, reverse=True))
# only inside "edge/arc/node/from/to/between X (and|to|-) Y" contexts, so ordinary words survive
NODE_CTX = re.compile(rf"\b(edge|arc|node|nodes|from|between|to)\s+({_L}|[a-z])\b(\s*(?:,|and|to|-|→)\s*)({_L}|[a-z])\b", re.I)

VOCAB = re.compile(r"\b(kruskal|prim|dijkstra|ford|bellman|könig|konig|spanning|tree|forest|cut|flow|augment\w*|dipath|digraph|"
                   r"dicircuit|circuit|cycle|arc|edge|node|potential|matching|cover|tsp|mst|bfs|topological|capacity|"
                   r"residual|auxiliary|bipartite|shortest|minimum|maximum|polynomial|neighbor|brute)\b", re.I)


def _letters(m):
    a, sep, b = m.group(2), m.group(3), m.group(4)
    return f"{m.group(1)} {LETTERS.get(a.lower(), a)}{sep}{LETTERS.get(b.lower(), b)}"


def normalize(text):
    t = ' '.join((text or '').split())
    for pat, rep in FIXES:
        t = re.sub(pat, rep, t, flags=re.I)
    t = NODE_CTX.sub(_letters, t)
    return t


def score(text):
    return len(VOCAB.findall(text)) + (2 if NODE_CTX.search(text) else 0)


def best_alternative(alternatives):
    """alternatives: list of (transcript, confidence). Returns (normalized best, original)."""
    best = None
    for k, (t, conf) in enumerate(alternatives):
        n = normalize(t)
        s = score(n) + 2 * (conf or 0) - 0.05 * k
        if best is None or s > best[0]:
            best = (s, n, t)
    return (best[1], best[2]) if best else ('', '')
