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
from .retrieval import find_concepts, retrieve, card_sources, CARDS, CARD_BY_ID
from .algorithms import kruskal, dijkstra, DEMO_NODES, DEMO_MST, DEMO_PATH
from .feedback import assess

UNITS = ['Problems and Algorithms', 'Minimum Spanning Trees', 'Shortest Paths', 'Maximum Flow']
MIN_BM25_ONLY = 5.0       # a concept matched only by word overlap must clear this to be trusted

INTENTS = [
    ('start', r"\b(start|begin)\b.*\b(lesson|lecture|unit)\b|mini-?lecture|^\s*start\s*$"),
    ('next', r"^\s*(next|continue|go on|keep going|move on|what'?s next|okay next|ok next)\b"),
    ('quiz', r"\b(quiz|test) me\b|check my understanding|ask me (a )?question"),
    ('compare', r"\b(difference|differ|versus|vs\.?|compare|compared|same as|different from)\b"),
    ('simplify', r"simpl|eli5|like i'?m (5|five|new|a beginner)|plain (english|words|language)|dumb it|confus|"
                 r"don'?t (get|understand)|\blost\b|too (hard|complex|complicated)|break (it|this) down|"
                 r"more basic|from scratch|beginner|intuition|in other words|say that again|another way"),
    ('example', r"\b(example|walk me through|walk through|step by step|demonstrate|trace|run (it|through))\b|show me"),
    ('why', r"\bwhy\b|how come|what'?s the (reason|point|idea)"),
]

DEMO_INTRO = {'kruskal': "Let's watch Kruskal run, step by step.", 'dijkstra': "Let's watch Dijkstra run, step by step."}


QUESTION_START = re.compile(r"^\s*(what|why|how|when|where|which|who|explain|tell|show|define|describe|give|walk|can|could|"
                            r"does|do|is|are|please|help|i (don'?t|dont|need|want))\b", re.I)
STATEMENT_MARK = re.compile(r"\b(i think|i guess|because|that means|isn'?t it|so (the|it|we)|it'?s|it is)\b", re.I)


def detect_intent(q, has_prev=False):
    for name, pat in INTENTS:
        if re.search(pat, q, re.I):
            return name
    # A statement in the student's own words (e.g. answering a check question) -> self-check mode.
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


def compose(card, intent, history, other=None, student_text=""):
    # Rule-based feedback abstains unless it recognizes a specific misconception or insight.
    again = times_explained(history, card['id']) >= 1
    if intent == 'quiz':
        return [f'Quick check on {card["title"]}. {card["check"]}']
    if intent == 'answer':
        label, opening = assess(card['id'], student_text)
        if label == 'ungraded':
            return [opening, f'{card["why"]}',
                    'Which part of your reasoning matches that explanation, and which part differs?']
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
    screen = '\n\n'.join(([note] if note else []) + paras)
    spoken = ' '.join(([note] if note else []) + paras)
    quote = evidence_line(sources)
    if quote:
        screen += '\n\n' + quote
        spoken += " I've put the matching lecture slides on screen."
    spoken += ' ' + (spoken_extra or 'Think about that one, then say next to continue, or ask me anything.')
    return {'answer': screen, 'spoken': spoken, 'sources': sources, 'mode': 'concept-cards+bm25',
            'concept_id': card['id'], 'title': card['title'], 'intent': intent,
            'predicted_topic': card['id'], 'topic_confidence': round(min(1.0, confidence / 20), 3)}


def answer(question, unit, history):
    if unit not in UNITS:
        raise ValueError('Invalid unit')
    prev = last_concept(history)
    intent = detect_intent(question, has_prev=prev is not None)
    cards = unit_cards(unit)

    # --- guided lesson flow ---
    if intent in ('start', 'next'):
        idx = 0
        if intent == 'next' and prev in CARD_BY_ID and CARD_BY_ID[prev]['unit'] == unit:
            idx = [c['id'] for c in cards].index(prev) + 1
        if idx >= len(cards):
            msg = f'That covers every concept in {unit}. Ask about anything you want to revisit, or say quiz me.'
            return {'answer': msg, 'spoken': msg, 'sources': [], 'mode': 'concept-cards+bm25', 'concept_id': prev,
                    'title': 'End of unit', 'intent': intent, 'predicted_topic': prev, 'topic_confidence': 1.0}
        card = cards[idx]
        intro = (f"Let's walk through {unit}, one idea at a time. Say next to move on, or interrupt me with a question anytime. "
                 if intent == 'start' else '')
        paras = [intro + f'Idea: {card["title"]}. ' + card['simple'], card['analogy'], 'For example: ' + card['example'],
                 f'Check yourself: {card["check"]}']
        return pack(card, intent, paras, card_sources(card, question)[:3], 20)

    # --- resolve concept ---
    ranked = find_concepts(question, unit, limit=3)
    confident = [r for r in ranked if r['alias_hit'] or r['score'] >= MIN_BM25_ONLY]
    card, other, conf = None, None, 0.0
    if intent == 'answer' and prev in CARD_BY_ID:
        card, conf = CARD_BY_ID[prev], 10.0            # the student is answering the check question I just asked
    elif confident:
        card, conf = confident[0]['card'], confident[0]['score']
        if len(confident) > 1:
            other = confident[1]['card']
    elif prev in CARD_BY_ID and (len(question.split()) <= 9 or intent != 'explain'):
        card, conf = CARD_BY_ID[prev], 10.0            # follow-up: "why?", "explain it more simply"
    elif intent == 'quiz' and cards:
        card, conf = cards[0], 10.0                    # "quiz me" with no context: start at the unit's first concept
    if intent == 'compare' and card is not None and other is None:
        if prev in CARD_BY_ID and prev != card['id']:
            other = CARD_BY_ID[prev]                       # "difference between that and Prim"
        else:
            other = CARD_BY_ID.get(next(iter(card.get('contrast', {})), None))
        if other is None:
            intent = 'explain'

    if card is None:
        hits = retrieve(question, unit)
        menu = topic_menu(unit)
        if hits:
            h = hits[0]
            msg = (f"I don't have a plain-language lesson that matches that exactly, but the closest lecture material is "
                   f"{page_label(h['pages'])} ({h['title']}): {h['excerpt']}\n\nCould you name the concept you mean? In this unit I can explain {menu}.")
            spoken = (f"I don't have a lesson that matches that exactly, but the closest lecture material is on {page_label(h['pages'])}. "
                      f"Could you name the concept you mean? In this unit I can explain {menu}.")
        else:
            msg = spoken = (f"That doesn't look like something in the {unit} unit. In this unit I can explain {menu}. "
                            "Which one would you like?")
        return {'answer': msg, 'spoken': spoken, 'sources': hits, 'mode': 'concept-cards+bm25', 'concept_id': None,
                'title': None, 'intent': intent, 'predicted_topic': None, 'topic_confidence': 0.0}

    note = f'That one is covered in the {card["unit"]} unit, so I will answer from there.' if card['unit'] != unit else ''
    spoken_extra = {'quiz': 'Take your time, then say next, or ask me to explain it.',
                    'answer': 'Say next to continue, or tell me which part felt different.'}.get(intent)
    return pack(card, intent, compose(card, intent, history, other, question), card_sources(card, question)[:3], conf, spoken_extra, note)
