"""One entry point for both tutoring engines, streaming or not.

Event protocol (also the Server-Sent Events protocol of /api/ask/stream):
  ('meta',    {engine, concept_id, title, intent, sources})   once, before any text
  ('delta',   {text})                                         answer text, in order
  ('replace', {text})                                         discard streamed text, show this instead
  ('notice',  {message})                                      non-fatal information (e.g. LLM not configured)
  ('done',    full result dict)                               always last
"""
import re, time

from . import grounding, llm, tutor
from .retrieval import card_sources, retrieve

ENGINES = ('auto', 'cards', 'llm')


def _pieces(text, words=3):
    toks = re.findall(r'\S+\s*', text)
    for i in range(0, len(toks), words):
        yield ''.join(toks[i:i + words])


def _meta(result):
    return {k: result.get(k) for k in ('engine', 'concept_id', 'title', 'intent', 'sources')}


def _cards(question, unit, history, delay, note=None):
    result = tutor.answer(question, unit, history)
    if note:
        result['engine'] = 'cards (llm-fallback)'
        result['fallback_reason'] = note
    yield 'meta', _meta(result)
    for p in _pieces(result['answer']):
        yield 'delta', {'text': p}
        if delay:
            time.sleep(delay)
    yield 'done', result


def _llm_sources(card, question, unit):
    if card is None:
        return retrieve(question, unit, limit=4)
    out = card_sources(card, question)[:3]
    for h in retrieve(question, card['unit'], limit=3):
        if len(out) >= 5:
            break
        if all(h['id'] != o['id'] for o in out):
            out.append(h)
    return out


def respond_stream(question, unit, history, engine='auto', delay=0.0, transport=None):
    if engine not in ENGINES:
        raise ValueError('engine must be auto, cards or llm')
    if unit not in tutor.UNITS:
        raise ValueError('Invalid unit')
    cfg = llm.config()
    use_llm = engine == 'llm' or (engine == 'auto' and cfg is not None)
    if use_llm and cfg is None and transport is None:
        yield 'notice', {'message': 'Generative engine is not configured on the server; using lesson cards.'}
        use_llm = False
    if not use_llm:
        yield from _cards(question, unit, history, delay)
        return

    if tutor.guard(question, unit, history) is not None:   # homework / coverage policy is deterministic
        yield from _cards(question, unit, history, delay)
        return
    r = tutor.resolve(question, unit, history)
    if r['intent'] in ('start', 'next', 'practice'):            # lesson navigation stays deterministic
        yield from _cards(question, unit, history, delay)
        return
    card, intent = r['card'], r['intent']
    sources = _llm_sources(card, question, unit)
    walk = tutor.DEMOS[card['id']]() if card and intent == 'example' and card['id'] in tutor.DEMOS else None
    system, messages = llm.build_prompt(question, unit, card, intent, sources, history, r['other'], walk)
    model = (cfg or {}).get('model', 'test-transport')
    base = {'engine': 'llm', 'mode': f'llm:{model}', 'concept_id': card['id'] if card else None,
            'title': card['title'] if card else None, 'intent': intent, 'sources': sources,
            'predicted_topic': card['id'] if card else None,
            'topic_confidence': round(min(1.0, r['conf'] / 20), 3)}
    yield 'meta', _meta(base)
    buf = []
    try:
        for t in llm.stream(system, messages, transport=transport, cfg=cfg or
                            {'provider': 'anthropic', 'url': 'test://', 'key': '', 'model': model}):
            buf.append(t)
            yield 'delta', {'text': t}
    except llm.LLMUnavailable as e:
        fb = tutor.answer(question, unit, history)
        fb['engine'], fb['fallback_reason'] = 'cards (llm-fallback)', str(e)[:200]
        yield 'replace', {'text': fb['answer']}
        yield 'done', fb
        return
    text = ''.join(buf).strip()
    if not text:
        fb = tutor.answer(question, unit, history)
        fb['engine'], fb['fallback_reason'] = 'cards (llm-fallback)', 'empty model response'
        yield 'replace', {'text': fb['answer']}
        yield 'done', fb
        return
    yield 'done', {**base, 'answer': text, 'spoken': llm.speakable(text),
                   'grounding': grounding.for_generated(text, sources)}


def respond(question, unit, history, engine='auto', transport=None):
    result, notices = None, []
    for ev, data in respond_stream(question, unit, history, engine, transport=transport):
        if ev == 'done':
            result = data
        elif ev == 'notice':
            notices.append(data['message'])
    if notices:
        result['notices'] = notices
    return result
