"""Full-course mode: every lecture slide taught in order, Aristotle-style but visual.

Each lesson is a list of steps. A step is one beat of teaching:
  say    what the tutor speaks (written for the ear: no symbols)
  text   what the tutor writes in the chat (clear prose; $math$ allowed; "- " bullets)
  draw   diagram operations applied as the step starts (see app/scenes.py OPS + figure/tour/note/hide)
  ask    optional check question: the lesson waits for the student's answer before continuing
  slides slide pages this step teaches (for citations and the coverage test)

Diagrams are REDRAWN from the slides (figures were transcribed from the PDF pages; where a figure was
too dense to reproduce, a smaller illustrative version is used and the text says so). Every number in
an algorithm run comes from tested code in app/algorithms.py, computed when the lesson is built.

Coverage: tests/test_course.py checks that every slide chunk in data/chunks.json is taught by some
lesson or is explicitly listed in SKIPPED (title pages, section dividers, "quiz" placeholders).
"""
import re

W, H = 560, 320


def fig(nodes, edges=(), directed=False):
    """nodes: {id: (x, y)} or {id: (x, y, style)} with style node|point|base; edges: (u, v[, label[, bend]])."""
    ns = []
    for k, v in nodes.items():
        ns.append({'id': k, 'x': v[0], 'y': v[1], 'style': v[2] if len(v) > 2 else 'node'})
    es = []
    for e in edges:
        u, v = e[0], e[1]
        lab = '' if len(e) < 3 or e[2] is None else str(e[2])
        bend = e[3] if len(e) > 3 else 0
        es.append({'id': f'{u}-{v}', 'u': u, 'v': v, 'label': lab, 'bend': bend})
    return {'width': W, 'height': H, 'directed': directed, 'nodes': ns, 'edges': es}


def all_ids(figure):
    return [n['id'] for n in figure['nodes']] + [e['id'] for e in figure['edges']]


class Lesson:
    def __init__(self, lid, unit, title, covers, goal):
        self.id, self.unit, self.title, self.covers, self.goal = lid, unit, title, list(covers), goal
        self.steps, self._pending_fig = [], None

    def figure(self, figure, reveal=True):
        self._pending_fig = (figure, reveal)
        return figure

    def step(self, say, text=None, draw=(), why=None, slides=(), edges=()):
        ops = []
        if self._pending_fig:
            f, rev = self._pending_fig
            ops.append({'op': 'figure', 'figure': f})
            if rev:
                ops.append({'op': 'reveal', 'ids': all_ids(f)})
            self._pending_fig = None
        self.steps.append({'say': say, 'text': text or say, 'draw': ops + list(draw), 'why': why or text or say,
                           'slides': list(slides), 'edges': list(edges)})
        return self

    def ask(self, q, expect, answer, say=None, hint=None, draw=(), slides=()):
        """expect: list of groups; each group is a list of regex alternatives. All groups => correct."""
        self.step(say or q, '**Your turn:** ' + q, draw, why=answer, slides=slides)
        self.steps[-1]['ask'] = {'q': q, 'expect': expect, 'answer': answer, 'hint': hint}
        return self

    def to_json(self):
        for i, s in enumerate(self.steps):
            s['i'] = i
        return {'id': self.id, 'unit': self.unit, 'title': self.title, 'goal': self.goal,
                'covers': self.covers, 'steps': self.steps}


DONT_KNOW = re.compile(r"\b(i )?(don'?t|do not) know\b|\bnot sure\b|\bno idea\b|\bskip\b|\btell me\b|\bgive up\b|\bshow me\b", re.I)


def check_answer(ask, reply):
    """Rule-based check of a short answer. Honest about what it can judge: unmatched -> 'unsure'."""
    reply = (reply or '').strip()
    if not reply or DONT_KNOW.search(reply):
        return {'verdict': 'revealed', 'feedback': "No problem. Here's how I'd answer it: " + ask['answer']}
    low = reply.lower()
    hits = [any(re.search(alt, low) for alt in group) for group in ask['expect']]
    if hits and all(hits):
        return {'verdict': 'correct', 'feedback': 'Yes, exactly. ' + ask['answer']}
    if any(hits):
        return {'verdict': 'partial', 'feedback': "You're on the right track. The full answer: " + ask['answer']}
    return {'verdict': 'unsure', 'feedback': "I can't tell for sure from that, so compare with how I'd put it: "
                                             + ask['answer'] + ' Does that match your reasoning?'}


_COURSE = None


def course():
    global _COURSE
    if _COURSE is None:
        from . import u1, u2, u3, u4
        lessons = [L.to_json() for m in (u1, u2, u3, u4) for L in m.lessons()]
        _COURSE = {'lessons': lessons, 'by_id': {l['id']: l for l in lessons}}
    return _COURSE


def outline():
    return [{'id': l['id'], 'unit': l['unit'], 'title': l['title'], 'goal': l['goal'], 'steps': len(l['steps']),
             'questions': sum(1 for s in l['steps'] if 'ask' in s)} for l in course()['lessons']]


# Slide chunks deliberately not taught as content (by chunk id in data/chunks.json).
SKIPPED = {0: 'title page', 22: 'title page', 23: 'section divider', 51: 'title page', 100: 'title page',
           102: 'section divider', 15: 'section divider (its topic is taught from chunk 16)',
           36: 'transition slide ("we now show the correctness…")', 69: 'transition slide',
           92: 'quiz placeholder (proof covered in the next slide)', 129: 'section divider'}
