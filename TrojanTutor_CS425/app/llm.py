"""Optional generative engine: a Socratic LLM constrained to the course evidence.

OFF by default. The offline card engine stays the reproducible baseline; this engine exists so
the research can compare "fixed authored lessons" with "grounded generative tutoring" on the
SAME concept resolution and the SAME retrieved slides (app.tutor.resolve + retrieval).

Enable (pick one):
  export TROJANTUTOR_LLM=anthropic  ANTHROPIC_API_KEY=...   [TROJANTUTOR_LLM_MODEL=claude-sonnet-5-5]
  export TROJANTUTOR_LLM=openai     OPENAI_API_KEY=...      TROJANTUTOR_LLM_MODEL=<model name>
         (TROJANTUTOR_LLM_BASE_URL=http://localhost:11434/v1 for an OpenAI-compatible local server)

Constraints enforced around the model, not just requested in the prompt:
  * it only ever sees the lesson card + numbered slide excerpts for the resolved concept;
  * every [n] it writes is validated against those sources (app.grounding) and the answer is
    labelled lecture-grounded / partially-grounded / not-grounded;
  * algorithm walkthroughs are NOT generated — the verified narration from app.algorithms is
    passed in and the model is told to use its numbers verbatim;
  * any provider error falls back to the offline card engine.
Standard library only (urllib); no SDK dependency.
"""
import json, os, re, urllib.request

PROVIDERS = {
    'anthropic': {'url': 'https://api.anthropic.com/v1/messages', 'key': 'ANTHROPIC_API_KEY',
                  'model': 'claude-sonnet-5-5'},
    'openai': {'url': 'https://api.openai.com/v1/chat/completions', 'key': 'OPENAI_API_KEY', 'model': None},
}
MAX_TOKENS = 600
TIMEOUT = 45


class LLMUnavailable(RuntimeError):
    pass


def config():
    name = os.getenv('TROJANTUTOR_LLM', 'off').lower()
    if name not in PROVIDERS:
        return None
    p = PROVIDERS[name]
    key = os.getenv(p['key'], '')
    base = os.getenv('TROJANTUTOR_LLM_BASE_URL')
    model = os.getenv('TROJANTUTOR_LLM_MODEL') or p['model']
    if not model or (not key and not base):
        return None
    url = p['url'] if not base else base.rstrip('/') + ('/messages' if name == 'anthropic' else '/chat/completions')
    return {'provider': name, 'url': url, 'key': key, 'model': model}


def available():
    return config() is not None


SYSTEM = """You are TrojanTutor, a Socratic tutor for the course "{course}", unit "{unit}".

Rules — follow all of them:
1. Use ONLY the LESSON NOTES and the numbered LECTURE SOURCES below. Do not add facts, theorem numbers,
   running times or definitions that are not in them.
2. Put a citation like [1] after every sentence that states a fact from a lecture source. Never cite a
   number that is not listed. The lesson notes are not citable; cite the slide they came from.
3. If the sources do not contain the answer, say exactly: "The lecture materials I have don't cover that."
   Then suggest which listed concept to ask about. Do not guess.
4. Teach Socratically: at most {max_words} words, one idea at a time, plain language first, then end with
   exactly ONE question that makes the student reason (not a yes/no question).
5. Write math in LaTeX between $...$ (inline) or $$...$$ (display). Match the slide notation.
6. If a VERIFIED WALKTHROUGH is given, use its numbers verbatim; never compute graph examples yourself.
7. Student intent for this turn: {intent}. {intent_rule}"""

INTENT_RULES = {
    'answer': ("The student is answering your previous question. Compare their reasoning with the reference "
               "reasoning. Say what is right, name the specific gap if any, and do not hand over the full answer; "
               "ask a guiding question instead."),
    'simplify': 'Use the analogy and the simplest wording; avoid notation unless asked.',
    'why': 'Focus on WHY it works (the reasoning), then the common trap.',
    'example': 'Walk through a concrete example (use the verified walkthrough if provided).',
    'compare': 'Contrast the two concepts directly; name the one key difference.',
    'quiz': 'Ask one check question about this concept and wait. Do not answer it.',
}


def build_prompt(question, unit, card, intent, sources, history, other=None, walkthrough=None,
                 course='CS 425 Introduction to Combinatorial Optimization', max_words=150):
    rule = INTENT_RULES.get(intent, 'Explain the concept clearly, then check understanding.')
    system = SYSTEM.format(course=course, unit=unit, max_words=max_words, intent=intent, intent_rule=rule)
    ctx = []
    if card:
        ctx.append('LESSON NOTES (authored from the slides; background, not citable):')
        for k in ('title', 'simple', 'analogy', 'example', 'why', 'trap', 'check'):
            ctx.append(f'- {k}: {card[k]}')
        if card.get('formula'):
            ctx.append(f"- formula (slide {card['formula']['ref']}): ${card['formula']['tex']}$")
    if other:
        ctx.append(f"CONTRAST CONCEPT: {other['title']}: {other['simple']}")
        c = card.get('contrast', {}).get(other['id']) or other.get('contrast', {}).get(card['id'])
        if c:
            ctx.append(f'- key difference: {c}')
    if walkthrough:
        ctx.append('VERIFIED WALKTHROUGH (from tested code; use verbatim): ' + walkthrough)
    ctx.append('LECTURE SOURCES:' if sources else 'LECTURE SOURCES: (none matched)')
    for i, s in enumerate(sources, 1):
        ctx.append(f"[{i}] {s['unit']}, slide {s['pages']} — {s['title']}: {s['text'][:900]}")
    messages = []
    for m in history[-6:]:
        role = 'user' if m['role'] == 'user' else 'assistant'
        messages.append({'role': role, 'content': m['content'][:1500]})
    messages.append({'role': 'user', 'content': '\n'.join(ctx) + f'\n\nSTUDENT: {question}'})
    # Providers require alternating roles starting with user.
    while messages and messages[0]['role'] != 'user':
        messages.pop(0)
    return system, messages


def _http_stream(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    except Exception as e:  # urllib raises several types; all mean "fall back"
        raise LLMUnavailable(f'{type(e).__name__}: {e}') from e
    with resp:
        for raw in resp:
            yield raw.decode('utf-8', 'replace').rstrip('\n')


def stream(system, messages, transport=None, cfg=None):
    """Yield text deltas. `transport(url, headers, body)` -> iterable of SSE lines (injectable for tests)."""
    cfg = cfg or config()
    if cfg is None:
        raise LLMUnavailable('LLM engine not configured')
    transport = transport or _http_stream
    if cfg['provider'] == 'anthropic':
        headers = {'content-type': 'application/json', 'x-api-key': cfg['key'], 'anthropic-version': '2023-06-01'}
        body = {'model': cfg['model'], 'max_tokens': MAX_TOKENS, 'system': system, 'messages': messages,
                'stream': True, 'temperature': 0.3}
    else:
        headers = {'content-type': 'application/json'}
        if cfg['key']:
            headers['authorization'] = f"Bearer {cfg['key']}"
        body = {'model': cfg['model'], 'max_tokens': MAX_TOKENS, 'stream': True, 'temperature': 0.3,
                'messages': [{'role': 'system', 'content': system}] + messages}
    for line in transport(cfg['url'], headers, body):
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if not data or data == '[DONE]':
            continue
        try:
            ev = json.loads(data)
        except ValueError:
            continue
        if cfg['provider'] == 'anthropic':
            if ev.get('type') == 'content_block_delta' and ev.get('delta', {}).get('type') == 'text_delta':
                yield ev['delta']['text']
            elif ev.get('type') == 'error':
                raise LLMUnavailable(str(ev.get('error')))
        else:
            for ch in ev.get('choices', []):
                t = (ch.get('delta') or {}).get('content')
                if t:
                    yield t


def speakable(text):
    """Text for speech synthesis: drop citations, replace display math, de-LaTeX inline math."""
    text = re.sub(r'\[\d{1,2}\]', '', text)
    text = re.sub(r'\$\$.*?\$\$', ' (the formula is on screen) ', text, flags=re.S)

    def inline(m):
        t = m.group(1)
        t = re.sub(r'\\(le|leq)\b', ' at most ', t)
        t = re.sub(r'\\(ge|geq)\b', ' at least ', t)
        t = re.sub(r'\\[a-zA-Z]+', ' ', t)
        return re.sub(r'[{}_^]', ' ', t)
    text = re.sub(r'\$(.+?)\$', inline, text)
    return re.sub(r'\s+', ' ', text).strip()
