"""FastAPI entrypoint.

Sessions persist in SQLite (app/sessions.py); answers come from app/engine.py, which serves the
offline lesson-card engine by default and an optional grounded LLM engine when configured.
"""
from pathlib import Path
import json, logging, os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.requests import Request

from . import llm, tts
from .scenes import build_scene, answer_interruption, SCENE_OF
from . import course as course_mod
from .speech import normalize as normalize_speech, best_alternative
from .algorithms import kruskal, dijkstra, DEMO_NODES, DEMO_MST, DEMO_PATH
from .engine import respond, respond_stream, ENGINES
from .ingest import load_manifest
from .interventions import intervene, reassess
from .pedagogical_retrieval import retrieve_evidence
from .retrieval import retrieve, CHUNKS, ALL_CHUNKS, DEPLOYMENT, CARDS
from .sessions import SessionStore
from .tutor import UNITS

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.12.0'
STREAM_DELAY = float(os.getenv('TROJANTUTOR_STREAM_DELAY', '0.025'))   # pacing for the offline engine only
app = FastAPI(title='TrojanTutor CS425', version=VERSION)
logger = logging.getLogger('trojantutor')
STORE = SessionStore()


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    # Do not leak stack traces, local file paths, or secrets into the browser.
    logger.exception('Unhandled error during %s %s', request.method, request.url.path)
    return JSONResponse(status_code=500, content={'detail': 'Unexpected backend error. Check the server terminal for the traceback.'})


app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')   # course PDFs are never served


class Question(BaseModel):
    session_id: str
    question: str = Field(min_length=1, max_length=1200)
    engine: str = 'auto'


class Search(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    unit: str | None = None


class EvidenceRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1200)
    unit: str | None = None
    concept: str | None = None
    student_explanation: str | None = None
    mode: str = 'hybrid'
    limit: int = Field(default=5, ge=1, le=25)
    lecture: str | None = None


class InterventionRequest(BaseModel):
    concept_id: str
    student_explanation: str = Field(min_length=1, max_length=3000)
    mode: str = 'pedagogical'


class ReassessmentRequest(BaseModel):
    concept_id: str
    student_explanation: str = Field(min_length=1, max_length=3000)


class CanvasQuestion(BaseModel):
    session_id: str
    concept_id: str
    step: int = Field(default=0, ge=0, le=500)
    question: str = Field(min_length=1, max_length=1200)
    engine: str = 'auto'


class CourseAnswer(BaseModel):
    session_id: str
    lesson_id: str
    step: int = Field(ge=0, le=500)
    answer: str = Field(default='', max_length=2000)


class CourseQuestion(BaseModel):
    session_id: str
    lesson_id: str
    step: int = Field(default=0, ge=0, le=500)
    question: str = Field(min_length=1, max_length=1200)
    engine: str = 'auto'


class CourseProgress(BaseModel):
    session_id: str
    lesson_id: str
    step: int = Field(ge=0, le=500)
    completed: bool = False


class Transcript(BaseModel):
    alternatives: list[list] = Field(default_factory=list)      # [[text, confidence], ...]
    text: str | None = None


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)


class GraphRequest(BaseModel):
    algorithm: str
    nodes: list[str] = Field(default_factory=lambda: DEMO_NODES.copy())
    edges: list[list] = Field(default_factory=list)
    start: str = 'A'


def _session_or_404(sid):
    s = STORE.get(sid)
    if not s:
        raise HTTPException(404, 'Unknown session')
    return s


@app.get('/')
def home():
    return FileResponse(ROOT / 'static/index.html')


@app.get('/api/health')
def health():
    cfg = llm.config()
    return {'status': 'ok', 'version': VERSION, 'unit_count': len(UNITS), 'chunks': len(CHUNKS),
            'chunks_excluded_by_permission': len(ALL_CHUNKS) - len(CHUNKS), 'deployment': DEPLOYMENT,
            'concept_cards': len(CARDS), 'tts': tts.config() is not None, 'llm': {'available': cfg is not None,
                                                 'provider': cfg and cfg['provider'], 'model': cfg and cfg['model']}}


@app.get('/api/units')
def units():
    return {'units': UNITS}


@app.get('/api/sources')
def sources():
    """Permission boundary, made visible: what material the tutor may use and under what status."""
    m = load_manifest()
    return {'deployment': DEPLOYMENT, 'policy': m['policy'],
            'sources': [{k: s[k] for k in ('file', 'unit', 'pages', 'status', 'approved_by')} for s in m['sources']]}


@app.post('/api/session')
def session(unit: str = 'Minimum Spanning Trees'):
    if unit not in UNITS:
        raise HTTPException(400, 'Unknown unit')
    sid = STORE.create(unit)
    return {'session_id': sid, 'unit': unit}


@app.get('/api/session/{sid}')
def session_summary(sid: str):
    s = STORE.summary(sid)
    if not s:
        raise HTTPException(404, 'Unknown session')
    return s


@app.post('/api/session/{sid}/unit')
def session_unit(sid: str, unit: str):
    _session_or_404(sid)
    if unit not in UNITS:
        raise HTTPException(400, 'Unknown unit')
    STORE.set_unit(sid, unit)
    return {'session_id': sid, 'unit': unit}


@app.delete('/api/session/{sid}')
def session_delete(sid: str):
    if not STORE.delete(sid):
        raise HTTPException(404, 'Unknown session')
    return {'deleted': sid}


def _check_engine(engine):
    if engine not in ENGINES:
        raise HTTPException(400, 'engine must be auto, cards or llm')


@app.post('/api/ask')
def ask(q: Question):
    s = _session_or_404(q.session_id)
    _check_engine(q.engine)
    try:
        result = respond(q.question, s['unit'], STORE.history(q.session_id), q.engine)
    except (RuntimeError, OSError, ImportError, ValueError) as e:
        logger.exception('Tutor inference failed')
        raise HTTPException(503, 'Tutor data unavailable. Run python -m app.ingest to rebuild data/chunks.json and check data/concepts.json.') from e
    STORE.append(q.session_id, q.question, result, s['unit'])
    return result


def _sse(event, data):
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


@app.post('/api/ask/stream')
def ask_stream(q: Question):
    """Server-Sent Events over POST (read with fetch + ReadableStream). See app/engine.py for events."""
    s = _session_or_404(q.session_id)
    _check_engine(q.engine)
    history = STORE.history(q.session_id)

    def gen():
        try:
            for ev, data in respond_stream(q.question, s['unit'], history, q.engine, delay=STREAM_DELAY):
                if ev == 'done':
                    STORE.append(q.session_id, q.question, data, s['unit'])
                yield _sse(ev, data)
        except Exception:  # the HTTP status is already sent; report inside the stream
            logger.exception('Streaming answer failed')
            yield _sse('error', {'detail': 'The tutor hit an error while answering. Check the server terminal.'})

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.get('/api/scenes')
def scenes():
    """Which concepts have a drawn (algorithm) scene; every concept has at least a board scene."""
    return {'scenes': [{'concept_id': c['id'], 'title': c['title'], 'unit': c['unit'],
                        'kind': SCENE_OF.get(c['id'], 'card')} for c in CARDS]}


@app.get('/api/scene/{concept_id}')
def scene(concept_id: str):
    try:
        return build_scene(concept_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post('/api/canvas/ask')
def canvas_ask(q: CanvasQuestion):
    """A question asked while a canvas lesson is playing. If it is about what is on the board (an edge,
    "why was that skipped?"), answer from the scene's verified run and say which step it refers to.
    Otherwise the normal tutor answers, with the scene's concept as conversational context."""
    s = _session_or_404(q.session_id)
    _check_engine(q.engine)
    try:
        sc = build_scene(q.concept_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    hit = answer_interruption(sc, q.step, q.question)
    if hit:
        result = {'answer': hit['answer'], 'spoken': hit['answer'], 'sources': sc['sources'], 'engine': 'canvas',
                  'mode': 'scene', 'concept_id': q.concept_id, 'title': sc['title'], 'intent': 'canvas-question',
                  'draw': hit['draw'], 'step': hit['step'],
                  'grounding': {'status': 'lecture-grounded', 'method': 'verified algorithm run / lesson card',
                                'label': 'Answered from the run on the board (tested code), tied to the lesson card.'}}
    else:
        history = STORE.history(q.session_id) + [{'role': 'assistant', 'content': sc['title'], 'concept': q.concept_id,
                                                   'intent': 'canvas'}]
        result = respond(q.question, sc['unit'] if sc['unit'] in UNITS else s['unit'], history, q.engine)
        result['draw'], result['step'] = [], q.step
    STORE.append(q.session_id, q.question, result, s['unit'])
    return result


def _lesson_or_404(lesson_id):
    les = course_mod.course()['by_id'].get(lesson_id)
    if not les:
        raise HTTPException(404, 'Unknown lesson')
    return les


@app.get('/api/course')
def course_outline(session_id: str | None = None):
    prog = STORE.progress(session_id) if session_id and STORE.get(session_id) else {}
    return {'lessons': course_mod.outline(), 'progress': prog, 'units': UNITS}


@app.get('/api/course/lesson/{lesson_id}')
def course_lesson(lesson_id: str):
    return _lesson_or_404(lesson_id)


@app.post('/api/course/check')
def course_check(q: CourseAnswer):
    _session_or_404(q.session_id)
    les = _lesson_or_404(q.lesson_id)
    if q.step >= len(les['steps']) or 'ask' not in les['steps'][q.step]:
        raise HTTPException(400, 'That step has no question')
    ask = les['steps'][q.step]['ask']
    res = course_mod.check_answer(ask, normalize_speech(q.answer))
    STORE.record_answer(q.session_id, q.lesson_id, res['verdict'] == 'correct')
    STORE.append(q.session_id, q.answer or '(no answer)', {'answer': res['feedback'], 'intent': 'course-answer:' + res['verdict'],
                 'engine': 'course', 'concept_id': None, 'sources': []}, les['unit'])
    return {**res, 'question': ask['q']}


def _figure_at(les, i):
    figure = None
    for st in les['steps'][:i + 1]:
        for op in st['draw']:
            if op['op'] == 'figure':
                figure = op['figure']
    return figure


@app.post('/api/course/ask')
def course_ask(q: CourseQuestion):
    """A question asked in the middle of a lesson: answered from the step on the board if it is about it,
    otherwise by the normal tutor with the lesson's unit as context."""
    s = _session_or_404(q.session_id)
    _check_engine(q.engine)
    les = _lesson_or_404(q.lesson_id)
    question = normalize_speech(q.question)
    i = min(q.step, len(les['steps']) - 1)
    figure = _figure_at(les, i)
    pseudo = {'graph': figure, 'steps': [st for st in les['steps']]}
    hit = answer_interruption(pseudo, i, question) if figure else None
    if hit and hit['answer'].strip():
        result = {'answer': hit['answer'], 'spoken': hit['answer'], 'sources': [], 'engine': 'course', 'mode': 'lesson',
                  'concept_id': None, 'title': les['title'], 'intent': 'lesson-question', 'draw': hit['draw'], 'step': hit['step'],
                  'grounding': {'status': 'lecture-grounded', 'method': 'lesson step (slides ' +
                                ', '.join(map(str, les['steps'][hit['step']]['slides'])) + ')',
                                'label': 'Answered from the lesson step on the board.'}}
    else:
        result = respond(question, les['unit'], STORE.history(q.session_id), q.engine)
        result['draw'], result['step'] = [], i
        # card answers end with chat-mode prompts ("say next to continue"); in a lesson, Continue resumes instead
        import re as _re
        result['spoken'] = _re.sub(r"\s*(Think about that one|Take your time|Say next to continue|Tell me your attempt).*$", '',
                                   result.get('spoken') or result['answer'])
    result['heard'] = question
    STORE.append(q.session_id, question, result, s['unit'])
    return result


@app.post('/api/course/progress')
def course_progress(q: CourseProgress):
    _session_or_404(q.session_id)
    _lesson_or_404(q.lesson_id)
    STORE.set_progress(q.session_id, q.lesson_id, q.step, q.completed)
    return {'ok': True}


@app.get('/api/slides')
def slides(unit: str, pages: str = ''):
    """Lecture chunks covering the given page numbers (comma-separated) of one unit: the evidence for a lesson step."""
    if unit not in UNITS:
        raise HTTPException(400, 'Unknown unit')
    want = {int(p) for p in pages.split(',') if p.strip().isdigit()}
    out = [c for c in CHUNKS if c['unit'] == unit and any(c['page_start'] <= p <= c['page_end'] for p in want)]
    from .retrieval import best_bullets
    return {'sources': [{**c, 'excerpt': best_bullets(c['text'], c['title'], n=2)} for c in out[:4]]}


@app.post('/api/speech/normalize')
def speech_normalize(q: Transcript):
    """Fix course vocabulary in a speech transcript and pick the best recogniser alternative."""
    alts = [(a[0], a[1] if len(a) > 1 else 0) for a in q.alternatives if a] or [(q.text or '', 1)]
    best, original = best_alternative(alts)
    return {'text': best, 'original': original, 'changed': best.strip().lower() != original.strip().lower()}


@app.post('/api/tts')
def speech(q: SpeechRequest):
    try:
        return Response(tts.synthesize(q.text), media_type='audio/mpeg')
    except tts.TTSUnavailable as e:
        raise HTTPException(503, str(e))


@app.post('/api/search')
def search(q: Search):
    if q.unit is not None and q.unit not in UNITS:
        raise HTTPException(400, 'Unknown unit')
    return {'sources': retrieve(q.query, q.unit)}


@app.post('/api/evidence')
def evidence(q: EvidenceRequest):
    if q.unit is not None and q.unit not in UNITS:
        raise HTTPException(400, 'Unknown unit')
    try:
        return retrieve_evidence(q.query, q.unit, q.concept, q.student_explanation, q.mode, q.limit, q.lecture)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/api/intervene')
def intervention(q: InterventionRequest):
    try:
        return intervene(q.concept_id, q.student_explanation, mode=q.mode)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/api/reassess')
def intervention_reassessment(q: ReassessmentRequest):
    try:
        return reassess(q.concept_id, q.student_explanation)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/api/algorithm')
def algorithm(q: GraphRequest):
    try:
        edges = q.edges or (DEMO_MST if q.algorithm == 'kruskal' else DEMO_PATH)
        if q.algorithm == 'kruskal':
            return {**kruskal(q.nodes, edges), 'nodes': q.nodes, 'input_edges': edges}
        if q.algorithm == 'dijkstra':
            return {**dijkstra(q.nodes, edges, q.start), 'nodes': q.nodes, 'input_edges': edges, 'start': q.start}
        raise ValueError('Choose kruskal or dijkstra')
    except ValueError as e:
        raise HTTPException(400, str(e))
