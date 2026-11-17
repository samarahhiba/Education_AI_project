"""TrojanTutor teaching engine.

Pipeline per question:
  1. Detect the student's INTENT (explain / simplify / why / example / compare / quiz / next / start).
  2. Resolve the CONCEPT: alias+BM25 match in the concept cards, falling back to the previous
     concept for follow-ups like "explain that more simply" or "why?".
  3. Compose a SPOKEN-FIRST answer from the lesson card (plain words -> analogy -> example),
     with slide evidence shown on screen. Demos (Kruskal, Dijkstra) are narrated from the
     verified algorithm code in app/algorithms.py, never from model arithmetic.
  4. Adapt: asking about the same concept again switches to a different angle.

No generative model is involved: every sentence is either authored lesson text, a narrated
output of tested code, or a cleaned excerpt of a lecture slide. That keeps it checkable.
"""
import re
from .retrieval import find_concepts, retrieve, card_sources, tokenize, CARDS, CARD_BY_ID
from .algorithms import kruskal, dijkstra, DEMO_NODES, DEMO_MST, DEMO_PATH
from .feedback import assess
from . import grounding
from . import exercises as ex_mod

UNITS = ['Problems and Algorithms', 'Minimum Spanning Trees', 'Shortest Paths', 'Maximum Flow']
MIN_BM25_ONLY = 5.0       # a concept matched only by word overlap must clear this to be trusted

INTENTS = [
    ('start', r"\b(start|begin)\b.*\b(lesson|lecture|unit)\b|mini-?lecture|^\s*start\s*$"),
    ('next', r"^\s*(next|continue|go on|keep going|move on|what'?s next|okay next|ok next)\b"),
    ('practice', r"\bpractice\b|\b(give|show) me (an? )?(exercise|problem)\b|problem to (try|solve)|exercise (to|i can) (try|do)"),
    ('quiz', r"\b(quiz|test) me\b|check my understanding|ask me (a )?question"),
    ('compare', r"\b(difference|differ|versus|vs\.?|compare|compared|same as|different from)\b"),
    ('simplify', r"simpl|eli5|like i'?m (5|five|new|a beginner)|plain (english|words|language)|dumb it|confus|"
                 r"don'?t (get|understand)|\blost\b|too (hard|complex|complicated)|break (it|this) down|"
                 r"more basic|from scratch|beginner|intuition|in other words|say that again|another way"),
    ('example', r"\b(example|walk me through|walk through|step by step|demonstrate|trace|run (it|through))\b|show me"),
    ('why', r"\bwhy\b|how come|what'?s the (reason|point|idea)"),
]

DEMO_INTRO = {'kruskal': "Let's watch Kruskal run, step by step.", 'dijkstra': "Let's watch Dijkstra run, step by step."}


# Spoken input has no "?" and often starts with fillers ("um", "so", "okay"), so strip those first.
FILLERS = re.compile(r"^\s*((um+|uh+|hmm+|so|okay|ok|well|hey|and|but|then|alright|right|wait|actually|now|also|"
                     r"yeah|yes|no|sorry|tutor|please)\b[\s,.!]*)+", re.I)
QUESTION_START = re.compile(r"^\s*(what|what'?s|why|how|how'?s|when|where|which|who|explain|tell|teach|show|define|"
                            r"describe|give|walk|go over|talk|remind|recap|summari[sz]e|compare|can|could|would|"
                            r"should|will|did|does|do|is|are|was|were|has|have|let'?s|lets|i'?d like|i would like|"
                            r"i (don'?t|dont|do not|still|need|want|wanna|am confused|'?m confused|get|didn'?t))\b", re.I)
STATEMENT_MARK = re.compile(r"\b(i think|i guess|because|that means|isn'?t it|so (the|it|we)|it'?s|it is)\b", re.I)


FOLLOW_UP = re.compile(r"\b(it|that|this|these|those|them|they|again|more|another|same|instead|example|why|how come|"
                       r"[A-Za-z]\s*(?:-|to|→)\s*[A-Za-z])\b", re.I)


def strip_fillers(q):
    return FILLERS.sub('', q).strip() or q.strip()


def detect_intent(q, has_prev=False):
    q = strip_fillers(q)
    for name, pat in INTENTS:
        if re.search(pat, q, re.I):
            return name
    # A statement in the student's own words (e.g. answering a check question) -> self-check mode.
    # resolve() still double-checks that it is really about the current concept.
    words = len(q.split())
    if '?' not in q and not QUESTION_START.match(q) and (
            (has_prev and words >= 5) or words >= 8 or (words >= 4 and STATEMENT_MARK.search(q))):
        return 'answer'
    return 'explain'


def unit_cards(unit):
    return [c for c in CARDS if c['unit'] == unit]


# ---------- narration of verified demos ----------
def _fmt(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def narrate_kruskal():
    res = kruskal(DEMO_NODES, DEMO_MST)
    edges = ', '.join(f'{u} {v} costs {_fmt(w)}' for u, v, w in DEMO_MST)
    out = [f'Here is a small graph with five nodes, A through E. The edges are: {edges}. '
           'Kruskal sorts them from cheapest to most expensive and goes down the list.']
    n_chosen = 0
    for st in res['steps']:
        u, v, w = st['edge']
        if st['decision'] == 'accept':
            n_chosen += 1
            out.append(f'Edge {u} {v}, cost {_fmt(w)}: accept. Running total {_fmt(st["total"])}.')
        else:
            out.append(f'Edge {u} {v}, cost {_fmt(w)}: skip, because {u} and {v} are already connected, '
                       'so this edge would close a loop.')
        if n_chosen == len(DEMO_NODES) - 1:
            break
    out.append(f'That is {n_chosen} edges for {len(DEMO_NODES)} nodes, so the tree is complete. '
               f'Total cost {_fmt(res["total"])}. Every remaining edge would only form a loop.')
    return ' '.join(out)


def narrate_dijkstra():
    res = dijkstra(DEMO_NODES, DEMO_PATH, 'A')
    arcs = ', '.join(f'{u} to {v} costs {_fmt(w)}' for u, v, w in DEMO_PATH)
    out = [f'Here is a small directed graph. The arcs are: {arcs}. We start at A.']
    for st in res['steps']:
        u = st['settled']
        d = st['distances'][u]
        ups = '; '.join(f'{x["to"]} becomes {_fmt(x["new_distance"])}' for x in st['updates'])
        out.append(f'Scan {u}, which is at distance {_fmt(d)}. ' + (f'Updates: {ups}.' if ups else 'No updates.'))
    fin = ', '.join(f'{k} {_fmt(v)}' for k, v in res['distances'].items())
    out.append(f'Final distances: {fin}. Notice B improved from 4 to 3 once C was scanned.')
    return ' '.join(out)


DEMOS = {'kruskal': narrate_kruskal, 'dijkstra': narrate_dijkstra}


# ---------- composition ----------
def first_sentence(text):
    m = re.match(r'(.+?[.!?])(\s|$)', text)
    return m.group(1) if m else text


def times_explained(history, cid):
    return sum(1 for m in history if m.get('role') == 'assistant' and m.get('concept') == cid)


def last_concept(history):
    for m in reversed(history):
        if m.get('role') == 'assistant' and m.get('concept'):
            return m['concept']
    return None


class ScreenOnly(str):
    """A paragraph shown on screen but not read aloud (formulas, slide quotes)."""


def formula_para(card):
    f = card.get('formula')
    if not f:
        return None
    return ScreenOnly(f'Formally (slide {f["ref"]}): $${f["tex"]}$$')


def compose(card, intent, history, other=None, student_text=""):
    # Rule-based feedback abstains unless it recognizes a specific misconception or insight.
    again = times_explained(history, card['id']) >= 1
    if intent == 'quiz':
        return [f'Quick check on {card["title"]}. {card["check"]}']
    if intent == 'answer':
        label, opening = assess(card['id'], student_text)
        if label == 'ungraded':
            return ["Let's compare your reasoning with how the lecture puts it.", card['why'],
                    'Which part of that matches what you said, and which part is different?']
        return [opening]
    if intent == 'compare' and other is not None:
        text = card.get('contrast', {}).get(other['id']) or other.get('contrast', {}).get(card['id'])
        paras = [f'{card["title"]}: {first_sentence(card["simple"])}',
                 f'{other["title"]}: {first_sentence(other["simple"])}']
        if text:
            paras.append(f'The key difference: {text}')
        return paras + [f'Check yourself: {card["check"]}']
    if intent == 'example':
        demo = DEMOS.get(card['id'])
        if demo:
            paras = [DEMO_INTRO[card['id']] + ' ' + demo()]
        else:
            paras = ['Here is a concrete example. ' + card['example'], first_sentence(card['simple'])]
    elif intent == 'why':
        paras = [f'Short version: {first_sentence(card["simple"])}',
                 f'The reason it works: {card["why"]}', f'Common trap: {card["trap"]}']
    elif again and intent in ('explain', 'simplify'):
        # Second pass on the same concept: do NOT repeat the first explanation. Compress, show it in action, name the trap.
        demo = DEMOS.get(card['id'])
        paras = ['Let me come at it from a different angle. In one sentence: ' + first_sentence(card['simple']),
                 ('Watch it run. ' + demo()) if demo else 'Here it is in action. ' + card['example'],
                 'The mistake people make: ' + card['trap']]
    elif intent == 'simplify':
        paras = ["Let's keep it really simple. " + card['analogy'], 'In plain words: ' + card['simple'],
                 'For example: ' + card['example']]
    else:
        paras = [card['simple'], card['analogy'], 'For example: ' + card['example']]
    f = formula_para(card)
    if f and intent in ('explain', 'why', 'example'):
        paras.append(f)
    return paras + [f'Check yourself: {card["check"]}']


def page_label(pages):
    return f'slides {pages.replace("-", " to ")}' if '-' in pages else f'slide {pages}'


def evidence_line(sources):
    if not sources:
        return ''
    s = sources[0]
    return f'From the lecture, {page_label(s["pages"])} ({s["title"]}): {s["excerpt"]}'


def topic_menu(unit):
    names = [c['title'] for c in unit_cards(unit)]
    return ', '.join(names[:-1]) + ', or ' + names[-1] if len(names) > 1 else ''.join(names)


def pack(card, intent, paras, sources, confidence, spoken_extra=None, note=''):
    screen = '\n\n'.join(([note] if note else []) + list(paras))
    spoken_paras = [p for p in paras if not isinstance(p, ScreenOnly)]
    spoken = ' '.join(([note] if note else []) + spoken_paras)
    if any(isinstance(p, ScreenOnly) for p in paras):
        spoken += ' The formal statement is on screen.'
    quote = evidence_line(sources)
    if quote:
        screen += '\n\n' + quote + ' [1]'
        spoken += " I've put the matching lecture slides on screen."
    spoken += ' ' + (spoken_extra or 'Think about that one, then say next to continue, or ask me anything.')
    return {'answer': screen, 'spoken': spoken, 'sources': sources, 'mode': 'concept-cards+bm25',
            'engine': 'cards', 'concept_id': card['id'], 'title': card['title'], 'intent': intent,
            'predicted_topic': card['id'], 'topic_confidence': round(min(1.0, confidence / 20), 3),
            'grounding': grounding.for_card(card, sources)}


def resolve(question, unit, history):
    """Decide intent and which lesson card(s) a question is about. Shared by the card engine and the
    optional LLM engine so both teach the same concept for the same question (fair comparison)."""
    if unit not in UNITS:
        raise ValueError('Invalid unit')
    prev = last_concept(history)
    intent = detect_intent(question, has_prev=prev is not None)
    cards = unit_cards(unit)
    card, other, conf = None, None, 0.0
    if intent in ('start', 'next'):
        idx = 0
        if intent == 'next' and prev in CARD_BY_ID and CARD_BY_ID[prev]['unit'] == unit:
            idx = [c['id'] for c in cards].index(prev) + 1
        card = cards[idx] if idx < len(cards) else None
        return {'intent': intent, 'card': card, 'other': None, 'conf': 20.0, 'prev': prev, 'end_of_unit': card is None}
    ranked = find_concepts(question, unit, limit=3)
    confident = [r for r in ranked if r['alias_hit'] or r['score'] >= MIN_BM25_ONLY]
    if intent == 'answer':
        # Only treat a statement as an answer if it is about the concept I just asked about. If it names a
        # different concept ("prim is the one that grows a tree"), or shares almost nothing with the current
        # lesson (a stray voice transcript), handle it as a request about whatever it names instead.
        named = [r for r in ranked if r['alias_hit']]
        cur = CARD_BY_ID.get(prev)
        overlap = len(set(tokenize(question)) & set(tokenize(' '.join([cur['title'], cur['simple'], cur['why'],
                                                                              cur['check']])))) if cur else 0
        names_other = named and prev not in [r['card']['id'] for r in named] and overlap < 3
        if cur is None:
            if not named:                       # no lesson context and no concept named: not an answer
                intent = 'explain'
        elif names_other or overlap < 2:
            intent = 'explain'
    if intent == 'answer' and prev in CARD_BY_ID:
        card, conf = CARD_BY_ID[prev], 10.0            # the student is answering the check question I just asked
    elif confident:
        card, conf = confident[0]['card'], confident[0]['score']
        if len(confident) > 1:
            other = confident[1]['card']
        # Follow-up on the concept we were just discussing ("why does the cycle matter?" after Kruskal):
        # keep that concept unless the question clearly names a different one.
        prev_hit = next((r for r in confident if r['card']['id'] == prev), None)
        if (prev_hit and prev_hit is not confident[0] and intent in ('why', 'simplify', 'example', 'explain')
                and prev_hit['score'] * 1.6 >= confident[0]['score']):
            card, conf, other = prev_hit['card'], prev_hit['score'], None
    elif prev in CARD_BY_ID and (intent != 'explain' or len(question.split()) <= 4 or FOLLOW_UP.search(question)):
        card, conf = CARD_BY_ID[prev], 10.0            # follow-up: "why?", "explain it more simply"
    elif intent in ('quiz', 'practice') and cards:
        card, conf = cards[0], 10.0                    # "quiz me" with no context: start at the unit's first concept
    if intent == 'compare' and card is not None and other is None:
        if prev in CARD_BY_ID and prev != card['id']:
            other = CARD_BY_ID[prev]                       # "difference between that and Prim"
        else:
            other = CARD_BY_ID.get(next(iter(card.get('contrast', {})), None))
        if other is None:
            intent = 'explain'
    return {'intent': intent, 'card': card, 'other': other, 'conf': conf, 'prev': prev, 'end_of_unit': False}


def _plain(answer_text, spoken, intent, status, label, card=None, sources=(), extra=None):
    out = {'answer': answer_text, 'spoken': spoken, 'sources': list(sources), 'mode': 'concept-cards+bm25',
           'engine': 'cards', 'concept_id': card['id'] if card else None, 'title': card['title'] if card else None,
           'intent': intent, 'predicted_topic': card['id'] if card else None, 'topic_confidence': 1.0 if card else 0.0,
           'grounding': {'status': status, 'label': label, 'method': 'policy'}}
    out.update(extra or {})
    return out


def _ex_name(ex):
    return f"Assignment {ex['assignment'][1:]}, Exercise {ex['number']}"


def guard(question, unit, history):
    """Policy checks that run BEFORE any engine teaches: coverage gaps and graded homework.
    Returns a finished response, or None to continue normally."""
    gap = ex_mod.uncovered_topic(question)
    if gap:
        msg = (f"That's about {gap['description']}. It isn't in the lecture slides I have, so I can't teach it "
               "from course material without guessing. If you add that lecture deck, I can cover it. "
               f"Meanwhile, in {unit} I can explain {topic_menu(unit)}.")
        return _plain(msg, msg, 'coverage-gap', 'not-covered', 'Not covered by the ingested lecture slides.',
                      extra={'coverage_gap': gap['term']})
    hit = ex_mod.homework_match(question)
    if hit:
        ex = hit['exercise']
        name = _ex_name(ex)
        if not ex.get('concepts'):
            msg = (f"This looks like {name}. Its topic isn't in the lecture slides I have, and it's graded homework, "
                   "so I can't help with it here. Your instructor's office hours or the course forum are the right place.")
            return _plain(msg, msg, 'homework', 'not-covered', 'Graded homework on an uncovered topic.',
                          extra={'homework_match': ex['id']})
        card = CARD_BY_ID[ex['concepts'][0]]
        srcs = card_sources(card, question)[:2]
        paras = [f"This looks like {name}. That's graded homework, so I won't write out a solution, "
                 "but I can help you get unstuck on the idea behind it.",
                 f"The concept you need is {card['title']}. {first_sentence(card['simple'])}",
                 f"Why it works: {card['why']}",
                 f"A common trap: {card['trap']}",
                 'What have you tried so far, and where exactly does it stop working?']
        out = pack(card, 'homework-hint', paras, srcs, 20,
                   spoken_extra='Tell me your attempt and I will point at the step to rethink.')
        out['homework_match'] = ex['id']
        out['grounding']['label'] = 'Hints only (graded homework). ' + out['grounding']['label']
        return out
    return None


def practice(card, history):
    posed = {m.get('exercise') for m in history if m.get('exercise')}
    ex = ex_mod.practice_for(card['id'], exclude=posed)
    if ex is None:
        paras = [f"I don't have an assignment problem on {card['title']} yet, so here's a check question instead.",
                 card['check']]
        return pack(card, 'practice', paras, card_sources(card, '')[:2], 20)
    kind = 'an optional practice exercise' if ex['optional'] else 'a past homework exercise'
    paras = [f"Here's {kind} on {card['title']}, from {_ex_name(ex)}:",
             ScreenOnly(ex_mod.clean_statement(ex)),
             f"Before you start, recall: {first_sentence(card['simple'])}",
             'Tell me your plan for the first step, and I will check the reasoning with you.']
    out = pack(card, 'practice', paras, card_sources(card, '')[:2], 20,
               spoken_extra='The problem statement is on screen. Tell me your plan for the first step.')
    out['exercise'] = ex['id']
    return out


def answer(question, unit, history):
    if unit not in UNITS:
        raise ValueError('Invalid unit')
    guarded = guard(question, unit, history)
    if guarded:
        return guarded
    r = resolve(question, unit, history)
    intent, card, other, conf, prev = r['intent'], r['card'], r['other'], r['conf'], r['prev']

    # --- guided lesson flow ---
    if intent in ('start', 'next'):
        if r['end_of_unit']:
            msg = f'That covers every concept in {unit}. Ask about anything you want to revisit, or say quiz me.'
            return {'answer': msg, 'spoken': msg, 'sources': [], 'mode': 'concept-cards+bm25', 'engine': 'cards',
                    'concept_id': prev, 'title': 'End of unit', 'intent': intent, 'predicted_topic': prev,
                    'topic_confidence': 1.0, 'grounding': {'status': 'n/a', 'label': '', 'method': 'navigation'}}
        intro = (f"Let's walk through {unit}, one idea at a time. Say next to move on, or interrupt me with a question anytime. "
                 if intent == 'start' else '')
        paras = [intro + f'Idea: {card["title"]}. ' + card['simple'], card['analogy'], 'For example: ' + card['example']]
        f = formula_para(card)
        if f:
            paras.append(f)
        paras.append(f'Check yourself: {card["check"]}')
        return pack(card, intent, paras, card_sources(card, question)[:3], 20)

    if card is None:
        hits = retrieve(question, unit)
        menu = topic_menu(unit)
        if hits:
            h = hits[0]
            msg = (f"I don't have a plain-language lesson that matches that exactly, but the closest lecture material is "
                   f"{page_label(h['pages'])} ({h['title']}): {h['excerpt']} [1]\n\nCould you name the concept you mean? In this unit I can explain {menu}.")
            spoken = (f"I don't have a lesson that matches that exactly, but the closest lecture material is on {page_label(h['pages'])}. "
                      f"Could you name the concept you mean? In this unit I can explain {menu}.")
        else:
            msg = spoken = (f"That doesn't look like something in the {unit} unit. In this unit I can explain {menu}. "
                            "Which one would you like?")
        return {'answer': msg, 'spoken': spoken, 'sources': hits, 'mode': 'concept-cards+bm25', 'engine': 'cards',
                'concept_id': None, 'title': None, 'intent': intent, 'predicted_topic': None, 'topic_confidence': 0.0,
                'grounding': grounding.for_retrieval(hits)}

    if intent == 'practice':
        return practice(card, history)
    note = f'That one is covered in the {card["unit"]} unit, so I will answer from there.' if card['unit'] != unit else ''
    spoken_extra = {'quiz': 'Take your time, then say next, or ask me to explain it.',
                    'answer': 'Say next to continue, or tell me which part felt different.'}.get(intent)
    return pack(card, intent, compose(card, intent, history, other, question), card_sources(card, question)[:3], conf, spoken_extra, note)
